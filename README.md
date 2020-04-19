# Jupyter Notebooks as PDF

This Jupyter notebook extension allows you to save your notebook as a PDF.

Three new features compared to the official "save as PDF" extension:
1. produce a PDF with the smallest number of page breaks,
1. the original notebook is attached to the PDF; and
1. this extension does not require LaTex.


## Install

To use this bundler you need to install it:
```
python -m pip install notebook-as-pdf
pyppeteer-install
```
The second command will download and setup Chromium. It is used to perform
the HTML to PDF conversion.


## Use it

Create a notebook and the click "File -> Download As". Click the new menu entry
called "PDF via HTML". Your notebook will be converted to a PDF on the fly
and then downloaded.

You will have to use Acrobat Reader to see the attachment to your PDF. Preview
on OSX can not display PDF attachments.
