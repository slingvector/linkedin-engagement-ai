"""
Carousel Renderer — FastAPI microservice (port 8002)
===================================================
Accepts slides JSON + brand_kit → renders a pixel-perfect branded HTML page
per slide → converts each to PDF pages using WeasyPrint → returns base64 PDF.

POST /render
POST /health
"""

import base64
import io

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from jinja2 import Environment, FileSystemLoader, select_autoescape

try:
    from weasyprint import HTML, CSS
    WEASYPRINT_AVAILABLE = True
except ImportError:
    WEASYPRINT_AVAILABLE = False

import structlog

logger = structlog.get_logger()

app = FastAPI(
    title="Carousel Renderer",
    version="1.0.0",
    description="Renders LinkedIn carousel slides as a branded PDF",
)

# ── Jinja2 template environment ───────────────────────────────────────────────
_template_dir = __file__.replace("main.py", "templates")
_jinja_env = Environment(
    loader=FileSystemLoader(_template_dir),
    autoescape=select_autoescape(["html"]),
)

# ── Request / Response schemas ────────────────────────────────────────────────

class Slide(BaseModel):
    slide_number: int
    headline: str
    body: str
    visual_suggestion: str

class BrandKit(BaseModel):
    primary_color: str = "#0A66C2"
    logo_url: str | None = None
    font_family: str = "Inter"
    author_name: str = ""
    author_tagline: str = ""

class RenderRequest(BaseModel):
    slides: list[Slide]
    brand_kit: BrandKit | dict = {}
    cover_hook: str = ""
    cta_text: str = "Follow for more →"

class RenderResponse(BaseModel):
    pdf_base64: str
    page_count: int


# ── Rendering Logic ───────────────────────────────────────────────────────────

def _render_slides_html(request: RenderRequest) -> str:
    """Render all slides into a single HTML document (one page per slide)."""
    bk = request.brand_kit if isinstance(request.brand_kit, dict) else request.brand_kit.model_dump()

    template = _jinja_env.get_template("slide.html")

    pages_html = []
    for slide in request.slides:
        is_cover = slide.slide_number == 1
        is_cta = slide.slide_number == len(request.slides)

        page = template.render(
            slide=slide,
            brand_kit=bk,
            is_cover=is_cover,
            is_cta=is_cta,
            cta_text=request.cta_text,
        )
        pages_html.append(page)

    # Wrap in a single document — WeasyPrint will create one PDF page per @page break
    combined = "\n".join(pages_html)
    return combined


def _html_to_pdf(html: str, brand_kit: dict) -> bytes:
    """Convert HTML string to PDF bytes using WeasyPrint."""
    font = brand_kit.get("font_family", "Inter")
    color = brand_kit.get("primary_color", "#0A66C2")

    base_css = CSS(string=f"""
        @import url('https://fonts.googleapis.com/css2?family={font}:wght@400;600;700;800&display=swap');

        @page {{
            size: 1080px 1080px;
            margin: 0;
        }}

        * {{
            font-family: '{font}', Inter, system-ui, sans-serif;
            box-sizing: border-box;
        }}

        body {{
            margin: 0;
            padding: 0;
            background: #111827;
        }}
    """)

    doc = HTML(string=html)
    return doc.write_pdf(stylesheets=[base_css])


# ── Endpoints ─────────────────────────────────────────────────────────────────

@app.get("/health")
async def health():
    return {
        "status": "ok",
        "service": "carousel_renderer",
        "weasyprint": WEASYPRINT_AVAILABLE,
    }


@app.post("/render", response_model=RenderResponse)
async def render(request: RenderRequest):
    """
    Render carousel slides as a branded PDF.
    Returns base64-encoded PDF bytes.
    """
    if not request.slides:
        raise HTTPException(status_code=400, detail="slides cannot be empty")

    logger.info("render_requested", slide_count=len(request.slides))

    bk = request.brand_kit if isinstance(request.brand_kit, dict) else request.brand_kit.model_dump()

    try:
        html = _render_slides_html(request)

        if WEASYPRINT_AVAILABLE:
            pdf_bytes = _html_to_pdf(html, bk)
        else:
            # Fallback: return HTML encoded as PDF placeholder for dev testing
            logger.warning("weasyprint_not_available_using_html_fallback")
            pdf_bytes = html.encode("utf-8")

        pdf_b64 = base64.b64encode(pdf_bytes).decode("utf-8")
        logger.info("render_complete", page_count=len(request.slides), pdf_size=len(pdf_bytes))

        return RenderResponse(
            pdf_base64=pdf_b64,
            page_count=len(request.slides),
        )
    except Exception as e:
        logger.error("render_failed", error=str(e))
        raise HTTPException(status_code=500, detail=f"Rendering failed: {e}")
