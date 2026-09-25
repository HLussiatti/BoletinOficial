"""Vercel Python WSGI entry point."""

from epe_boletin.cloud_web import CloudWeb

app = CloudWeb()
