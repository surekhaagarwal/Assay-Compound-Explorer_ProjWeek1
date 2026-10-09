"""Serve Streamlit at /assay-bench and redirect existing root preview links."""

import os
from pathlib import Path

import streamlit as st
from starlette.responses import RedirectResponse
from starlette.routing import Route


async def redirect_to_assay_bench(request):
    query = f"?{request.url.query}" if request.url.query else ""
    return RedirectResponse(f"/assay-bench/{query}", status_code=307)


application = st.App(
    Path(__file__).with_name("app.py"),
    routes=[Route("/", redirect_to_assay_bench)],
)


if __name__ == "__main__":
    application.run(
        config={
            "server.address": "0.0.0.0",
            "server.port": int(os.environ.get("PORT", "20861")),
            "server.baseUrlPath": "assay-bench",
            "server.headless": True,
            "browser.gatherUsageStats": False,
        }
    )
