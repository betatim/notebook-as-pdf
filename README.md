# Jupyter Notebooks as PDF

[![Binder](https://mybinder.org/badge_logo.svg)](https://mybinder.org/v2/gh/betatim/notebook-as-pdf/master)

This Jupyter notebook extension allows you to save your notebook as a PDF.

Three new features compared to the official "save as PDF" extension:
1. produce a PDF with the smallest number of page breaks,
1. the original notebook is attached to the PDF; and
1. this extension does not require LaTex.

The created PDF will have as few pages as possible, in many cases only one. This is useful if you are exporting your notebook to a PDF for sharing with others who will view it on a screen.

Every `<h1>` tag in the notebook will be converted into a entry in the table of contents of the PDF.

To make it easier to reproduce the contents of the PDF at a later date the original notebook is attached to the PDF. Unfortunately not all PDF viewers know how to deal with attachments. PDF viewers known to support downloading of file attachments are: Acrobat Reader, pdf.js and evince. The `pdftk` CLI program can also extract attached files from a PDF. Preview for OSX does not know how to display/give you access to attachments of PDF files.


## Install

To use this bundler you need to install it:
```
python -m pip install -U notebook-as-pdf
pyppeteer-install
```
The second command will download and setup Chromium. It is used to perform
the HTML to PDF conversion.

On linux you probably also need to install some or all of the APT packages
listed in [`binder/apt.txt`](binder/apt.txt).


## Use it

Create a notebook and the click "File -> Download As". Click the new menu entry
called "PDF via HTML". Your notebook will be converted to a PDF on the fly
and then downloaded.

You can also use it with `nbconvert`:
```
jupyter-nbconvert --to PDFviaHTML example.ipynb
```
which will create a file called `example.pdf`.

You will have to use Acrobat Reader to see the attachment to your PDF. Preview
on OSX can not display PDF attachments.
