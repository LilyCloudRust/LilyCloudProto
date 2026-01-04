import os
import urllib.parse
from email.utils import format_datetime
from typing import Annotated
from xml.etree.ElementTree import Element, SubElement, tostring

from fastapi import APIRouter, Depends, Header, Request, Response
from fastapi.responses import StreamingResponse
from fastapi.security import HTTPBasic, HTTPBasicCredentials

from lilycloudproto.dependencies import get_auth_service, get_storage_service
from lilycloudproto.domain.entities.user import User
from lilycloudproto.domain.values.files.file import File, Type
from lilycloudproto.domain.values.files.list import ListArgs
from lilycloudproto.domain.values.files.sort import SortBy, SortOrder
from lilycloudproto.error import ConflictError, NotFoundError
from lilycloudproto.infra.services.auth_service import AuthService

router = APIRouter(prefix="/webdav", tags=["WebDAV"])
security = HTTPBasic()

# WebDAV XML Namespace.
WEBDAV_NS = "DAV:"


async def get_current_user(
    credentials: Annotated[HTTPBasicCredentials, Depends(security)],
    auth_service: AuthService = Depends(get_auth_service),
) -> User:
    user = await auth_service.authenticate_user_basic(
        credentials.username, credentials.password
    )
    if not user:
        raise Exception("Unauthorized")
    return user


def create_prop_response(file: File, base_url: str) -> Element:
    response = Element(f"{{{WEBDAV_NS}}}response")
    href = SubElement(response, f"{{{WEBDAV_NS}}}href")
    rel_path = file.path if file.path.startswith("/") else "/" + file.path
    safe_path = urllib.parse.quote(rel_path)
    href.text = f"/webdav{safe_path}"

    propstat = SubElement(response, f"{{{WEBDAV_NS}}}propstat")
    prop = SubElement(propstat, f"{{{WEBDAV_NS}}}prop")

    # Display Name.
    displayname = SubElement(prop, f"{{{WEBDAV_NS}}}displayname")
    displayname.text = file.name

    # Resource Type.
    resourcetype = SubElement(prop, f"{{{WEBDAV_NS}}}resourcetype")
    if file.type == Type.DIRECTORY:
        _ = SubElement(resourcetype, f"{{{WEBDAV_NS}}}collection")

    # Properties.
    if file.type == Type.FILE:
        getcontentlength = SubElement(prop, f"{{{WEBDAV_NS}}}getcontentlength")
        getcontentlength.text = str(file.size)

        getcontenttype = SubElement(prop, f"{{{WEBDAV_NS}}}getcontenttype")
        getcontenttype.text = file.mime_type

    # Dates (RFC 1123 format).
    creationdate = SubElement(prop, f"{{{WEBDAV_NS}}}creationdate")
    creationdate.text = file.created_at.isoformat()

    getlastmodified = SubElement(prop, f"{{{WEBDAV_NS}}}getlastmodified")
    getlastmodified.text = format_datetime(file.modified_at)

    # Status.
    status_el = SubElement(propstat, f"{{{WEBDAV_NS}}}status")
    status_el.text = "HTTP/1.1 200 OK"

    return response


@router.api_route("/{path:path}", methods=["PROPFIND"])
async def webdav_propfind(
    path: str,
    request: Request,
    user: Annotated[User, Depends(get_current_user)],
    depth: Annotated[str | None, Header()] = "1",
) -> Response:
    storage = get_storage_service(request)
    real_path = path if path else "."

    driver = storage.get_driver(real_path)

    try:
        current_file = driver.info(real_path)
    except NotFoundError:
        return Response(status_code=404)

    multistatus = Element(f"{{{WEBDAV_NS}}}multistatus")
    multistatus.set("xmlns:D", WEBDAV_NS)
    multistatus.append(create_prop_response(current_file, str(request.base_url)))

    if current_file.type == Type.DIRECTORY and depth != "0":
        try:
            args = ListArgs(
                path=real_path,
                sort_by=SortBy.NAME,
                sort_order=SortOrder.ASC,
            )
            children = driver.list_dir(args)
            for child in children:
                multistatus.append(create_prop_response(child, str(request.base_url)))
        except Exception:
            pass

    xml_str = tostring(  # pyright: ignore[reportAny]
        multistatus, encoding="utf-8", xml_declaration=True
    )
    return Response(content=xml_str, status_code=207, media_type="application/xml")


@router.get("/{path:path}")
async def webdav_get(
    path: str, request: Request, user: Annotated[User, Depends(get_current_user)]
) -> Response:
    storage = get_storage_service(request)
    driver = storage.get_driver(path)

    try:
        info = driver.info(path)
        if info.type == Type.DIRECTORY:
            return Response(status_code=200)
        generator = driver.read(path)

        return StreamingResponse(
            generator,
            media_type=info.mime_type,
            headers={"Content-Length": str(info.size)},
        )
    except NotFoundError:
        return Response(status_code=404)
    except Exception as error:
        return Response(status_code=500, content=str(error))


@router.put("/{path:path}")
async def webdav_put(
    path: str, request: Request, user: Annotated[User, Depends(get_current_user)]
) -> Response:
    storage = get_storage_service(request)
    driver = storage.get_driver(path)
    try:
        await driver.write(path, request.stream())
        return Response(status_code=201)
    except Exception as error:
        return Response(status_code=500, content=str(error))


@router.delete("/{path:path}")
async def webdav_delete(
    path: str, request: Request, user: Annotated[User, Depends(get_current_user)]
) -> Response:
    storage = get_storage_service(request)
    driver = storage.get_driver(path)
    dirname = os.path.dirname(path)
    basename = os.path.basename(path)
    if not basename:
        return Response(status_code=403, content="Cannot delete root")

    try:
        await driver.delete(dirname, [basename])
        return Response(status_code=204)
    except NotFoundError:
        return Response(status_code=404)
    except Exception as error:
        return Response(status_code=500, content=str(error))


@router.api_route("/{path:path}", methods=["MKCOL"])
async def webdav_mkcol(
    path: str, request: Request, user: Annotated[User, Depends(get_current_user)]
) -> Response:
    storage = get_storage_service(request)
    driver = storage.get_driver(path)

    try:
        _ = driver.mkdir(path)
        return Response(status_code=201)
    except ConflictError:
        return Response(status_code=405)  # 405 Method Not Allowed / 409 Conflict
    except Exception as error:
        return Response(status_code=500, content=str(error))


@router.api_route("/{path:path}", methods=["MOVE", "COPY"])
async def webdav_move_copy(
    path: str,
    request: Request,
    user: Annotated[User, Depends(get_current_user)],
    destination: Annotated[str, Header()],
) -> Response:
    """
    Handle MOVE and COPY WebDAV methods.
    """
    storage = get_storage_service(request)
    driver = storage.get_driver(path)
    parsed_dest = urllib.parse.urlparse(destination)
    dest_path_raw = parsed_dest.path
    mount_prefix = "/webdav"
    if dest_path_raw.startswith(mount_prefix):
        dest_path = dest_path_raw[len(mount_prefix) :]
    else:
        dest_path = dest_path_raw
    dest_path = dest_path.lstrip("/")
    dest_path = urllib.parse.unquote(dest_path)

    src_dir = os.path.dirname(path)
    src_name = os.path.basename(path)
    dst_dir = os.path.dirname(dest_path)
    dst_name = os.path.basename(dest_path)

    try:
        if request.method == "MOVE":
            await driver.rename(path, dest_path)
        elif src_name == dst_name:
            await driver.copy(src_dir, dst_dir, [src_name])
        elif src_name != dst_name:
            return Response(
                status_code=501,
                content="Copy with rename not fully supported yet.",
            )
        else:
            await driver.copy(src_dir, dst_dir, [src_name])

        return Response(status_code=201)
    except ConflictError:
        return Response(status_code=409)
    except NotFoundError:
        return Response(status_code=404)
    except Exception as error:
        return Response(status_code=500, content=str(error))


@router.options("/{path:path}")
async def webdav_options(_path: str) -> Response:
    return Response(
        headers={
            "DAV": "1, 2",
            "Allow": (
                "OPTIONS, GET, HEAD, POST, PUT, DELETE, TRACE, COPY, MOVE, MKCOL, "
                "PROPFIND, PROPPATCH, LOCK, UNLOCK"
            ),
        }
    )
