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

from traitlets import Bool, default

import PyPDF2

from nbconvert.exporters import HTMLExporter
from nbconvert.exporters import TemplateExporter


async def html_to_pdf(html_file, pdf_file, pyppeteer_args=None):
    """Convert a HTML file to a PDF"""
    browser = await launch(
        handleSIGINT=False,
        handleSIGTERM=False,
        handleSIGHUP=False,
        args=pyppeteer_args or [],
    )
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
            offsetWidth: document.body.offsetWidth,
            offsetHeight: document.body.offsetHeight,
            deviceScaleFactor: window.devicePixelRatio,
        }
    }"""
    )
    width = dimensions["width"]
    height = dimensions["height"]

    await page.evaluate(
        """
    function getOffset( el ) {
        var _x = 0;
        var _y = 0;
        while( el && !isNaN( el.offsetLeft ) && !isNaN( el.offsetTop ) ) {
            _x += el.offsetLeft - el.scrollLeft;
            _y += el.offsetTop - el.scrollTop;
            el = el.offsetParent;
        }
        return { top: _y, left: _x };
        }
    """,
        force_expr=True,
    )

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
                /* Jupyterlab based HTML uses these classes */
                .jp-Cell-inputWrapper {
                    page-break-inside: avoid;
                }
                .jp-Cell-outputWrapper {
                    page-break-inside: avoid;
                }
                .jp-Notebook {
                    margin: 0px;
                }
                /* Hide the message box used by MathJax */
                #MathJax_Message {
                    display: none;
                }
         """
        }
    )

    await page.pdf(
        {
            "path": pdf_file,
            # Adobe can not display pages longer than 200inches. So we limit
            # ourselves to that and start a new page if needed.
            "width": min(width + 2, 200 * 72),
            "height": min(height + 2, 200 * 72),
            "printBackground": True,
            "margin": page_margins,
        }
    )

    headings = await page.evaluate(
        """() => {
        var vals = []
        for (const elem of document.getElementsByTagName("h1")) {
            vals.push({ top: getOffset(elem).top * (1-72/288), text: elem.innerText })
        }
        for (const elem of document.getElementsByTagName("h2")) {
            vals.push({ top: getOffset(elem).top * (1-72/288), text: "∙ " + elem.innerText })
        }
        return vals
    }"""
    )

    await browser.close()

    return headings


def finish_pdf(pdf_in, pdf_out, notebook, headings):
    """Add finishing touches to the PDF file.

    To make the PDF nicer we:

    * attach the original notebook to the PDF for reference
    * add bookmarks pointing to the headers in a notebook
    """
    pdf = PyPDF2.PdfFileWriter()
    pdf.appendPagesFromReader(PyPDF2.PdfFileReader(pdf_in, "rb"))
    pdf.addAttachment(notebook["file_name"], notebook["contents"])

    for heading in sorted(headings, key=lambda x: x["top"]):
        page_num = int(heading["top"]) // (200 * 72)

        page_height = pdf.getPage(page_num).artBox[-1]

        # position on the page as measured from the bottom of the page
        # with a bit of leeway so that clicking the bookmark doesn't put
        # the heading right at the border
        on_page_pos = page_height - (int(heading["top"]) % (200 * 72)) + 20

        # there is no nice way of passing the "zoom arguments" at the very
        # end of the function call without explicitly listing all the parameters
        # of the function. We can't use keyword arguments :(
        pdf.addBookmark(
            heading["text"],
            page_num,
            None,
            None,
            False,
            False,
            "/XYZ",
            0,
            on_page_pos,
            None,
        )

    with open(pdf_out, "wb") as fp:
        pdf.write(fp)


async def notebook_to_pdf(
    html_notebook, pdf_path, pyppeteer_args=None,
):
    """Convert HTML representation of a notebook to PDF"""
    with tempfile.NamedTemporaryFile(suffix=".html") as f:
        f.write(html_notebook.encode())
        f.flush()
        heading_positions = await html_to_pdf(f.name, pdf_path, pyppeteer_args)

    return heading_positions


class PDFExporter(TemplateExporter):
    """Convert a notebook to a PDF

    Expose this package's functionality to nbconvert
    """

    enabled = True
    # a thread pool to run our async event loop. We use our own
    # because `from_notebook_node` isn't async but sometimes is called
    # inside a tornado app that already has an event loop
    pool = concurrent.futures.ThreadPoolExecutor()

    export_from_notebook = "PDF via HTML"

    @default("file_extension")
    def _file_extension_default(self):
        return ".pdf"

    # make sure the HTML template is used even though we are using .pdf as
    # file extension
    template_extension = ".html.j2"

    # This value is used to inform browsers about the mimetype of the file
    # when people download the file we generated
    output_mimetype = "application/pdf"

    no_sandbox = Bool(True, help=("Disable chrome sandboxing."),).tag(config=True)

    def from_notebook_node(self, notebook, resources=None, **kwargs):
        html_exporter = HTMLExporter(config=self.config, parent=self)
        html_notebook, resources = html_exporter.from_notebook_node(
            notebook, resources=resources, **kwargs
        )

        # if it is unset or an empty value, set it
        if resources.get("ipywidgets_base_url", "") == "":
            resources["ipywidgets_base_url"] = "https://unpkg.com/"

        with tempfile.TemporaryDirectory(suffix="nb-as-pdf") as name:
            pdf_fname = os.path.join(name, "output.pdf")
            pdf_fname2 = os.path.join(name, "output-with-attachment.pdf")
            pyppeteer_args = ["--no-sandbox"] if self.no_sandbox else None

            heading_positions = self.pool.submit(
                asyncio.run,
                notebook_to_pdf(
                    html_notebook, pdf_fname, pyppeteer_args=pyppeteer_args,
                ),
            ).result()
            resources["output_extension"] = ".pdf"

            finish_pdf(
                pdf_fname,
                pdf_fname2,
                {
                    "file_name": f"{resources['metadata']['name']}.ipynb",
                    "contents": nbformat.writes(notebook).encode("utf-8"),
                },
                heading_positions,
            )

            with open(pdf_fname2, "rb") as f:
                pdf_bytes = f.read()

        # This sets the mimetype to what we really want (PDF) after all the
        # template loading is over (for which it needs to be set to HTML)
        self.output_mimetype = "application/pdf"

        return (pdf_bytes, resources)
