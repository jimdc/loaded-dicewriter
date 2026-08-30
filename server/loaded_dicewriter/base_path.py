"""ASGI middleware: accept APP_BASE_PATH-prefixed requests on a root-mounted app.

Primary hub path (strip_prefix:true): gateway strips `/loaded-dicewriter` and
forwards `/x` to this process — routes stay at web root; no middleware needed.

Also supports strip_prefix:false and local checks that leave the slug intact:
when a request arrives as `/loaded-dicewriter/...`, this middleware rewrites it
to the internal route (`/api/...`, `/assets/...`, SPA). Root probes stay reachable
unprefixed for gateway health checks.
"""

from __future__ import annotations

from starlette.types import ASGIApp, Receive, Scope, Send

from loaded_dicewriter.settings import app_base_prefix


class AppBasePathMiddleware:
    """Strip a configured URL prefix before routing (no-op when base is `/`)."""

    def __init__(self, app: ASGIApp, base_path: str = "/") -> None:
        self.app = app
        self.prefix = app_base_prefix(base_path)

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if self.prefix and scope["type"] in ("http", "websocket"):
            path = scope.get("path") or ""
            if path == self.prefix or path.startswith(f"{self.prefix}/"):
                remainder = path[len(self.prefix) :] or "/"
                root = scope.get("root_path") or ""
                new_scope = dict(scope)
                new_scope["path"] = remainder
                new_scope["root_path"] = f"{root}{self.prefix}"
                new_scope["raw_path"] = remainder.encode("utf-8")
                scope = new_scope
        await self.app(scope, receive, send)
