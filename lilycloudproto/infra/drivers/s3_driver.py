import asyncio
import mimetypes
import os
from collections.abc import AsyncGenerator, Awaitable, Callable
from datetime import datetime
from typing import TYPE_CHECKING, Any, override

from boto3.session import Session
from botocore.client import BaseClient
from botocore.config import Config as BotoConfig
from botocore.exceptions import ClientError

from lilycloudproto.domain.driver import Base, Driver
from lilycloudproto.domain.entities.storage import Storage
from lilycloudproto.domain.values.admin.storage import S3Config, StorageType
from lilycloudproto.domain.values.files.file import File, Type
from lilycloudproto.domain.values.files.list import ListArgs
from lilycloudproto.domain.values.files.search import SearchArgs
from lilycloudproto.domain.values.files.sort import SortArgs
from lilycloudproto.error import (
    BadRequestError,
    ConflictError,
    InternalServerError,
    NotFoundError,
)


class S3Driver(Driver):
    bucket: str
    client: BaseClient
    root_prefix: str
    trash_prefix: str
    mount_path: str

    def __init__(
        self, storage: Storage, base: Base = Base.REGULAR, share_path: str | None = None
    ):
        if storage.type != StorageType.S3:
            raise ValueError(
                f"S3Driver requires storage type 's3', got '{storage.type}'."
            )
        super().__init__(storage, base, share_path)

        try:
            config = S3Config.model_validate(storage.config)
        except Exception as error:
            raise ValueError(f"Invalid S3 storage config: {error}") from error

        session = Session(
            aws_access_key_id=config.access_key,
            aws_secret_access_key=config.secret_key,
            aws_session_token=config.session_token,
            region_name=config.region or config.endpoint_region_override,
        )
        boto_cfg = BotoConfig(
            s3={"addressing_style": "path" if config.use_path_style else "auto"}
        )
        self.client = session.client(
            "s3",
            endpoint_url=config.endpoint,
            config=boto_cfg,
            region_name=config.region or config.endpoint_region_override,
        )

        self.bucket = config.bucket
        self.root_prefix = self._normalize_prefix(config.prefix)
        self.trash_prefix = f"{self.root_prefix}.trash/"
        self.mount_path = self._normalize_mount(storage.mount_path)

    @override
    def list_dir(self, args: ListArgs) -> list[File]:
        prefix = self._path_to_key(args.path or "/", ensure_dir=True)
        files: list[File] = []
        paginator = self.client.get_paginator("list_objects_v2")
        page_iterator = paginator.paginate(
            Bucket=self.bucket, Prefix=prefix, Delimiter="/"
        )

        found_any = False
        for page in page_iterator:
            found_any = found_any or page.get("KeyCount", 0) > 0
            for common in page.get("CommonPrefixes", []):
                dir_name = common["Prefix"][len(prefix) :].rstrip("/")
                if not dir_name:
                    continue
                logical = self._join_logical(args.path, dir_name)
                now = datetime.now()
                files.append(
                    File(
                        name=dir_name,
                        path=logical,
                        type=Type.DIRECTORY,
                        size=0,
                        mime_type="inode/directory",
                        created_at=now,
                        modified_at=now,
                        accessed_at=now,
                    )
                )
            for obj in page.get("Contents", []):
                key = obj["Key"]
                if key.endswith("/") and key == prefix:
                    continue
                name = key[len(prefix) :]
                if not name:
                    continue
                logical = self._join_logical(args.path, name)
                ts = obj.get("LastModified", datetime.now())
                files.append(
                    File(
                        name=name,
                        path=logical,
                        type=Type.FILE,
                        size=int(obj.get("Size", 0)),
                        mime_type=self._guess_mime(name),
                        created_at=ts,
                        modified_at=ts,
                        accessed_at=ts,
                    )
                )

        # If nothing found, verify directory existence.
        if (
            prefix not in {"", "/"}
            and not found_any
            and args.path not in {"/", self.mount_path}
        ):
            try:
                _ = self.client.head_object(Bucket=self.bucket, Key=prefix)
                found_any = True
            except ClientError as error:
                if error.response.get("Error", {}).get("Code") != "404":
                    raise self._wrap_error(error) from error

        if not found_any and args.path not in {"/", self.mount_path}:
            raise NotFoundError(f"Directory not found at '{args.path}'.")

        return self._sort_files(files, args)

    @override
    def info(self, path: str) -> File:
        if not path or path == "/":
            now = datetime.now()
            return File(
                name="/",
                path="/",
                type=Type.DIRECTORY,
                size=0,
                mime_type="inode/directory",
                created_at=now,
                modified_at=now,
                accessed_at=now,
            )

        key = self._path_to_key(path, ensure_dir=False)
        try:
            head = self.client.head_object(Bucket=self.bucket, Key=key)
            ts = head.get("LastModified", datetime.now())
            mime = head.get("ContentType") or self._guess_mime(path)
            return File(
                name=os.path.basename(path.rstrip("/")) or "/",
                path=path,
                type=Type.FILE,
                size=int(head.get("ContentLength", 0)),
                mime_type=mime,
                created_at=ts,
                modified_at=ts,
                accessed_at=ts,
            )
        except ClientError as error:
            if error.response.get("Error", {}).get("Code") not in {"404", "NoSuchKey"}:
                raise self._wrap_error(error) from error

        dir_prefix = self._ensure_dir_suffix(key) if key else ""
        if dir_prefix == "":
            now = datetime.now()
            return File(
                name="/",
                path="/",
                type=Type.DIRECTORY,
                size=0,
                mime_type="inode/directory",
                created_at=now,
                modified_at=now,
                accessed_at=now,
            )
        resp = self.client.list_objects_v2(
            Bucket=self.bucket, Prefix=dir_prefix, MaxKeys=1
        )
        if resp.get("KeyCount", 0) == 0:
            raise NotFoundError(f"File not found at '{path}'.")
        now = datetime.now()
        return File(
            name=os.path.basename(path.rstrip("/")) or "/",
            path=path,
            type=Type.DIRECTORY,
            size=0,
            mime_type="inode/directory",
            created_at=now,
            modified_at=now,
            accessed_at=now,
        )

    @override
    def search(self, args: SearchArgs) -> list[File]:
        prefix = self._path_to_key(args.path, ensure_dir=True)
        paginator = self.client.get_paginator("list_objects_v2")
        page_iterator = paginator.paginate(Bucket=self.bucket, Prefix=prefix)
        result: list[File] = []

        for page in page_iterator:
            for obj in page.get("Contents", []):
                key = obj["Key"]
                if key.endswith("/"):
                    continue
                logical_path = self._key_to_logical(key)
                name = os.path.basename(logical_path)
                mime = self._guess_mime(name)

                if args.keyword and args.keyword.lower() not in name.lower():
                    continue
                if args.mime_type and args.mime_type.lower() not in mime.lower():
                    continue
                if args.type and args.type != Type.FILE:
                    continue

                ts = obj.get("LastModified", datetime.now())
                result.append(
                    File(
                        name=name,
                        path=logical_path,
                        type=Type.FILE,
                        size=int(obj.get("Size", 0)),
                        mime_type=mime,
                        created_at=ts,
                        modified_at=ts,
                        accessed_at=ts,
                    )
                )

        return self._sort_files(result, args)

    @override
    def mkdir(self, path: str, parents: bool = False) -> File:
        key = self._ensure_dir_suffix(self._path_to_key(path, ensure_dir=False))
        resp = self.client.list_objects_v2(Bucket=self.bucket, Prefix=key, MaxKeys=1)
        if resp.get("KeyCount", 0) > 0:
            raise ConflictError(f"Directory already exists at '{path}'.")
        try:
            _ = self.client.put_object(Bucket=self.bucket, Key=key)
        except ClientError as error:
            raise self._wrap_error(error) from error
        return self.info(path)

    @override
    async def copy(
        self,
        src_dir: str,
        dst_dir: str,
        file_names: list[str],
        progress_callback: Callable[[int, int], Awaitable[None]] | None = None,
    ) -> None:
        total = len(file_names)
        for index, name in enumerate(file_names, 1):
            src_key = self._path_to_key(os.path.join(src_dir, name), ensure_dir=False)
            dst_key = self._path_to_key(os.path.join(dst_dir, name), ensure_dir=False)
            try:
                await asyncio.to_thread(
                    self.client.copy,
                    {"Bucket": self.bucket, "Key": src_key},
                    self.bucket,
                    dst_key,
                )
            except ClientError as error:
                raise self._wrap_error(error) from error
            if progress_callback:
                await progress_callback(index, total)
            await asyncio.sleep(0)

    @override
    async def move(
        self,
        src_dir: str,
        dst_dir: str,
        file_names: list[str],
        progress_callback: Callable[[int, int], Awaitable[None]] | None = None,
    ) -> None:
        await self.copy(src_dir, dst_dir, file_names, progress_callback)
        await self.delete(src_dir, file_names, None)

    @override
    async def delete(
        self,
        dir: str,
        file_names: list[str],
        progress_callback: Callable[[int, int], Awaitable[None]] | None = None,
    ) -> None:
        total = len(file_names)
        for index, name in enumerate(file_names, 1):
            key = self._path_to_key(os.path.join(dir, name), ensure_dir=False)
            try:
                await asyncio.to_thread(
                    self.client.delete_object, Bucket=self.bucket, Key=key
                )
            except ClientError as error:
                raise self._wrap_error(error) from error
            if progress_callback:
                await progress_callback(index, total)
            await asyncio.sleep(0)

    @override
    async def write(self, path: str, content_stream: AsyncGenerator[bytes]) -> None:
        key = self._path_to_key(path, ensure_dir=False)
        body = bytearray()
        async for chunk in content_stream:
            body.extend(chunk)
        mime = self._guess_mime(path)
        try:
            await asyncio.to_thread(
                self.client.put_object,
                Bucket=self.bucket,
                Key=key,
                Body=bytes(body),
                ContentType=mime,
            )
        except ClientError as error:
            raise self._wrap_error(error) from error

    @override
    def read(self, path: str, chunk_size: int = 1024 * 64) -> AsyncGenerator[bytes]:
        key = self._path_to_key(path, ensure_dir=False)

        async def _reader() -> AsyncGenerator[bytes]:
            try:
                resp = await asyncio.to_thread(
                    self.client.get_object, Bucket=self.bucket, Key=key
                )
            except ClientError as error:
                raise self._wrap_error(error) from error
            stream = resp["Body"]
            while True:
                chunk = await asyncio.to_thread(stream.read, chunk_size)
                if not chunk:
                    break
                yield chunk

        return _reader()

    @override
    async def get_link(self, path: str) -> str | None:
        key = self._path_to_key(path, ensure_dir=False)
        try:
            url = await asyncio.to_thread(
                self.client.generate_presigned_url,
                ClientMethod="get_object",
                Params={"Bucket": self.bucket, "Key": key},
                ExpiresIn=3600,
            )
            return str(url)
        except ClientError as error:
            raise self._wrap_error(error) from error

    @override
    async def rename(self, src_path: str, dst_path: str) -> None:
        src_dir = os.path.dirname(src_path)
        dst_dir = os.path.dirname(dst_path)
        name = os.path.basename(src_path)
        await self.copy(src_dir, dst_dir, [name])
        await self.delete(src_dir, [name], None)

    @override
    async def trash(
        self,
        dir: str,
        file_names: list[str],
        progress_callback: Callable[[int, int], Awaitable[None]] | None = None,
    ) -> None:
        total = len(file_names)
        for index, name in enumerate(file_names, 1):
            src_key = self._path_to_key(os.path.join(dir, name), ensure_dir=False)
            rel = self._strip_mount(os.path.join(dir, name))
            dst_key = f"{self.trash_prefix}{rel}"
            try:
                await asyncio.to_thread(
                    self.client.copy,
                    {"Bucket": self.bucket, "Key": src_key},
                    self.bucket,
                    dst_key,
                )
                await asyncio.to_thread(
                    self.client.delete_object, Bucket=self.bucket, Key=src_key
                )
            except ClientError as error:
                raise self._wrap_error(error) from error
            if progress_callback:
                await progress_callback(index, total)
            await asyncio.sleep(0)

    @override
    async def restore(
        self,
        src_paths: list[str],
        dst_paths: list[str],
        progress_callback: Callable[[int, int], Awaitable[None]] | None = None,
    ) -> None:
        if len(src_paths) != len(dst_paths):
            raise ValueError("src_paths and dst_paths must have the same length.")
        total = len(src_paths)

        for index, (src, dst) in enumerate(zip(src_paths, dst_paths, strict=True), 1):
            trash_rel = self._strip_mount(src)
            src_key = f"{self.trash_prefix}{trash_rel}"
            dst_key = self._path_to_key(dst, ensure_dir=False)
            try:
                await asyncio.to_thread(
                    self.client.copy,
                    {"Bucket": self.bucket, "Key": src_key},
                    self.bucket,
                    dst_key,
                )
                await asyncio.to_thread(
                    self.client.delete_object, Bucket=self.bucket, Key=src_key
                )
            except ClientError as error:
                raise self._wrap_error(error) from error
            if progress_callback:
                await progress_callback(index, total)
            await asyncio.sleep(0)

    # Helpers
    def _normalize_mount(self, mount_path: str) -> str:
        mount = mount_path.strip()
        if not mount.startswith("/"):
            mount = "/" + mount
        return mount.rstrip("/") or "/"

    def _normalize_prefix(self, prefix: str | None) -> str:
        if not prefix:
            return ""
        p = prefix.strip("/")
        return f"{p}/" if p else ""

    def _strip_mount(self, logical_path: str) -> str:
        norm = logical_path.replace("\\", "/")
        if not norm.startswith("/"):
            norm = "/" + norm
        if not norm.startswith(self.mount_path):
            raise BadRequestError("Path is outside the storage mount.")
        rel = norm[len(self.mount_path) :].lstrip("/")
        if ".." in rel.split("/"):
            raise BadRequestError("Path traversal detected.")
        return rel

    def _path_to_key(self, logical_path: str, ensure_dir: bool) -> str:
        rel = self._strip_mount(logical_path)
        prefix = f"{self.root_prefix}{rel}" if rel else self.root_prefix
        if self.base == Base.TRASH:
            prefix = f"{self.trash_prefix}{rel}"
        elif self.base == Base.SHARE:
            raise BadRequestError("SHARE base is not implemented for S3Driver.")
        if ensure_dir and prefix:
            prefix = self._ensure_dir_suffix(prefix)
        return prefix

    def _ensure_dir_suffix(self, key: str) -> str:
        return key if key.endswith("/") else f"{key}/"

    def _join_logical(self, base_path: str, name: str) -> str:
        base_norm = base_path.rstrip("/")
        if not base_norm:
            base_norm = "/"
        joined = f"{base_norm}/{name}" if base_norm != "/" else f"/{name}"
        return joined.replace("//", "/")

    def _key_to_logical(self, key: str) -> str:
        rel = key[len(self.root_prefix) :].lstrip("/")
        logical = f"{self.mount_path}/{rel}" if self.mount_path != "/" else f"/{rel}"
        return logical.replace("//", "/")

    def _guess_mime(self, name: str) -> str:
        mime, _ = mimetypes.guess_type(name)
        return mime or "application/octet-stream"

    def _wrap_error(self, error: ClientError) -> Exception:
        code = error.response.get("Error", {}).get("Code", "")
        if code in {"404", "NoSuchKey", "NotFound"}:
            return NotFoundError("Object not found.")
        if code in {"403", "AccessDenied"}:
            return BadRequestError("Access denied to S3 object.")
        if code in {"409", "BucketAlreadyOwnedByYou", "BucketAlreadyExists"}:
            return ConflictError("Resource conflict in S3 operation.")
        return InternalServerError(str(error))

    def _sort_files(self, files: list[File], args: SortArgs) -> list[File]:
        reverse = args.sort_order == "desc"
        sort_key: dict[str, Callable[[File], Any]] = {
            "name": lambda file: file.name,
            "size": lambda file: file.size,
            "created": lambda file: file.created_at,
            "modified": lambda file: file.modified_at,
            "accessed": lambda file: file.accessed_at,
            "type": lambda file: file.mime_type,
        }
        files.sort(key=sort_key[args.sort_by], reverse=reverse)
        if args.dir_first:
            files.sort(key=lambda file: file.type == Type.FILE)
        return files
