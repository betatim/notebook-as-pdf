"""
Export a notebook to a one page PDF
"""
import asyncio
import os
import tempfile

import concurrent.futures

import nbformat
import nbconvert

from pyppeteer import launch

from traitlets import default

import PyPDF2

from nbconvert.exporters import Exporter


async def html_to_pdf(html_file, pdf_file):
    """Convert a HTML file to a PDF"""
    browser = await launch(handleSIGINT=False, handleSIGTERM=False, handleSIGHUP=False)
    page = await browser.newPage()
    await page.setViewport(dict(width=994, height=768))
    await page.emulateMedia("screen")

    await page.goto(f"file:///{html_file}", {"waitUntil": ["networkidle2"]})

    page_margins = {
        "left": "0px",
        "right": "0px",
        "top": "0px",
        "bottom": "0px",
    }

    dimensions = await page.evaluate(
        """() => {
        return {
            width: document.body.scrollWidth,
            height: document.body.scrollHeight,
            offsetHeight: document.body.offsetHeight,
            deviceScaleFactor: window.devicePixelRatio,
        }
    }"""
    )
    width = dimensions["width"]
    height = dimensions["height"]

    await page.addStyleTag(
        {
            "content": """
                #notebook-container {
                    box-shadow: none;
                    padding: unset
                }
                div.cell {
                    page-break-inside: avoid;
                }
                div.output_wrapper {
                    page-break-inside: avoid;
                }
                div.output {
                    page-break-inside: avoid;
                }
         """
        }
    )

    await page.pdf(
        {
            "path": pdf_file,
            "width": width,
            # Adobe can not display pages longer than 200inches. So we limit
            # ourselves to that and start a new page if needed.
            "height": min(height, 200 * 72),
            "printBackground": True,
            "margin": page_margins,
        }
    )

    await browser.close()


def attach_notebook(pdf_in, pdf_out, notebook):
    pdf = PyPDF2.PdfFileWriter()
    pdf.appendPagesFromReader(PyPDF2.PdfFileReader(pdf_in, "rb"))
    pdf.addAttachment(notebook["file_name"], notebook["contents"])

    with open(pdf_out, "wb") as fp:
        pdf.write(fp)


async def notebook_to_pdf(notebook, pdf_path, config=None, resources=None, **kwargs):
    """Convert a notebook to PDF"""
    if config is None:
        config = {}
    exporter = nbconvert.HTMLExporter(config=config)
    exported_html, _ = exporter.from_notebook_node(
        notebook, resources=resources, **kwargs
    )

    with tempfile.NamedTemporaryFile(suffix=".html") as f:
        f.write(exported_html.encode())
        f.flush()
        await html_to_pdf(f.name, pdf_path)


class PDFExporter(Exporter):
    """Convert a notebook to a PDF

    Expose this package's functionality to nbconvert
    """

    # a thread pool to run our async event loop. We use our own
    # because `from_notebook_node` isn't async but sometimes is called
    # inside a tornado app that already has an event loop
    pool = concurrent.futures.ThreadPoolExecutor()

    export_from_notebook = "PDF via HTML"
    output_mimetype = "application/pdf"

    @default("file_extension")
    def _file_extension_default(self):
        return ".pdf"

    def __init__(self, config=None, **kw):
        with_default_config = self.default_config
        if config:
            with_default_config.merge(config)

        super().__init__(config=with_default_config, **kw)

    def from_notebook_node(self, notebook, resources=None, **kwargs):
        notebook, resources = super().from_notebook_node(
            notebook, resources=resources, **kwargs
        )

        # if it is unset or an empty value, set it
        if resources.get("ipywidgets_base_url", "") == "":
            resources["ipywidgets_base_url"] = "https://unpkg.com/"

        with tempfile.TemporaryDirectory(suffix="nb-as-pdf") as name:
            pdf_fname = os.path.join(name, "output.pdf")
            pdf_fname2 = os.path.join(name, "output-with-attachment.pdf")

            self.pool.submit(
                asyncio.run,
                notebook_to_pdf(
                    notebook,
                    pdf_fname,
                    config=self.config,
                    resources=resources,
                    **kwargs,
                ),
            ).result()
            resources["output_extension"] = ".pdf"

            attach_notebook(
                pdf_fname,
                pdf_fname2,
                {
                    "file_name": f"{resources['metadata']['name']}.ipynb",
                    "contents": nbformat.writes(notebook).encode("utf-8"),
                },
            )

            with open(pdf_fname2, "rb") as f:
                pdf_bytes = f.read()

        return (pdf_bytes, resources)
