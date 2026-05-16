"""File conversion utilities for presentation files.

Converts PPT/PPTX/PDF/KEY files to individual slide images using:
- LibreOffice headless for PPT/PPTX/KEY → PDF conversion
- pdf2image for PDF → PNG slide images
"""

import asyncio
import logging
import os
import tempfile
from pathlib import Path

logger = logging.getLogger(__name__)

# Conversion timeout in seconds
CONVERSION_TIMEOUT = 120


async def convert_to_slides(file_data: bytes, extension: str) -> list[bytes]:
    """Convert a presentation file to a list of slide images (PNG bytes).

    Args:
        file_data: Raw bytes of the presentation file.
        extension: File extension (e.g., '.pptx', '.pdf', '.ppt', '.key').

    Returns:
        List of PNG image bytes, one per slide.

    Raises:
        asyncio.TimeoutError: If conversion exceeds 120 seconds.
        RuntimeError: If conversion fails for any other reason.
    """
    ext = extension.lower()

    if ext == ".pdf":
        return await _convert_pdf_to_images(file_data)
    elif ext in (".ppt", ".pptx", ".key"):
        return await _convert_office_to_images(file_data, ext)
    else:
        raise RuntimeError(f"Unsupported file extension: {ext}")


async def _convert_pdf_to_images(pdf_data: bytes) -> list[bytes]:
    """Convert PDF bytes to a list of PNG image bytes using pdf2image.

    Runs in a thread pool to avoid blocking the event loop.
    """

    def _do_convert() -> list[bytes]:
        from pdf2image import convert_from_bytes

        images = convert_from_bytes(pdf_data, dpi=150, fmt="png")
        result = []
        for img in images:
            from io import BytesIO

            buf = BytesIO()
            img.save(buf, format="PNG")
            result.append(buf.getvalue())
        return result

    try:
        return await asyncio.wait_for(
            asyncio.get_event_loop().run_in_executor(None, _do_convert),
            timeout=CONVERSION_TIMEOUT,
        )
    except asyncio.TimeoutError:
        logger.error("PDF conversion timed out after %d seconds", CONVERSION_TIMEOUT)
        raise
    except Exception as exc:
        logger.error("PDF conversion failed: %s", exc)
        raise RuntimeError(f"PDF conversion failed: {exc}") from exc


async def _convert_office_to_images(file_data: bytes, extension: str) -> list[bytes]:
    """Convert PPT/PPTX/KEY to slide images via LibreOffice headless → PDF → images.

    Steps:
    1. Write the file to a temp directory
    2. Run LibreOffice headless to convert to PDF
    3. Convert the resulting PDF to images using pdf2image
    """
    with tempfile.TemporaryDirectory() as tmpdir:
        # Write the source file
        input_filename = f"presentation{extension}"
        input_path = Path(tmpdir) / input_filename
        input_path.write_bytes(file_data)

        # Convert to PDF using LibreOffice headless
        try:
            process = await asyncio.wait_for(
                _run_libreoffice(str(input_path), tmpdir),
                timeout=CONVERSION_TIMEOUT,
            )
        except asyncio.TimeoutError:
            logger.error(
                "LibreOffice conversion timed out after %d seconds",
                CONVERSION_TIMEOUT,
            )
            raise

        if process.returncode != 0:
            stderr_output = process.stderr.decode() if process.stderr else "unknown error"
            logger.error("LibreOffice conversion failed: %s", stderr_output)
            raise RuntimeError(f"LibreOffice conversion failed: {stderr_output}")

        # Find the output PDF
        pdf_path = Path(tmpdir) / "presentation.pdf"
        if not pdf_path.exists():
            # LibreOffice may use a different output name
            pdf_files = list(Path(tmpdir).glob("*.pdf"))
            if not pdf_files:
                raise RuntimeError(
                    "LibreOffice conversion produced no PDF output"
                )
            pdf_path = pdf_files[0]

        # Convert PDF to images
        pdf_data = pdf_path.read_bytes()
        return await _convert_pdf_to_images(pdf_data)


async def _run_libreoffice(input_path: str, output_dir: str):
    """Run LibreOffice headless to convert a file to PDF.

    Args:
        input_path: Path to the input file.
        output_dir: Directory where the PDF output will be written.

    Returns:
        The completed subprocess.
    """
    cmd = [
        "libreoffice",
        "--headless",
        "--convert-to",
        "pdf",
        "--outdir",
        output_dir,
        input_path,
    ]

    # On Windows, try soffice.exe as well
    if os.name == "nt":
        cmd[0] = "soffice"

    process = await asyncio.create_subprocess_exec(
        *cmd,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
    )
    await process.communicate()
    return process
