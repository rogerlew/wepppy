# **LaTeX instructions**

Acquired June 12, 2026 from https://www.elsevier.com/researcher/author/policies-and-guidelines/latex-instructions

* [The Elsevier article class](https://www.elsevier.com/researcher/author/policies-and-guidelines/latex-instructions#0-the-elsevier-article-class)  
* [FAQs](https://www.elsevier.com/researcher/author/policies-and-guidelines/latex-instructions#1-faqs)  
* [Preparing CRC journal articles](https://www.elsevier.com/researcher/author/policies-and-guidelines/latex-instructions#2-preparing-crc-journal-articles)

[Download the journal article template package](https://assets.ctfassets.net/o78em1y1w4i4/4MpsJHO0MOJ2xZuwGTAbOZ/7bc64af36477c5d6cfce335a1f872363/elsarticle.zip)

## **The Elsevier article class**

The Elsevier article class helps you to format the frontmatter of your manuscript properly. It is part of the elsarticle package. This package is contained in most TeX distributions and is available in the template. The [elsarticle documentation](https://assets.ctfassets.net/o78em1y1w4i4/3ro3yQff1q67JHmLi1sAqV/1348e3852f277867230fc4b84a801734/elsdoc-1.pdf) and some common templates and bibliographic styles are part of this package as well.  
Two additional class files and templates are available for single and double column. These can be downloaded from [here](https://assets.ctfassets.net/o78em1y1w4i4/5uFmLZJTPDMAUjFnHRpjj8/6f19a979146eb93263763d87a894ab0d/els-cas-templates.zip).

### **Elsevier reference styles**

Some journals require a specific reference style. Please check the Guide for Authors for the journal requirement. The relevant bibliographic styles for LaTeX are packed with the sample manuscript are available in the “doc” folder.

## **Submitting your manuscript**

Most journals accept a PDF of your manuscript at initial submission.  
**When you are asked to submit your manuscript source files, do the following if PDF version is allowed:**

* Build a PDF of your manuscript source files on your computer and attach it with item type 'Manuscript'.  
* Bundle all manuscript source files in a single archive and attach it with item type 'LaTeX source files'. Source files include LaTeX files, BibTeX files, figures, tables, all LaTeX classes and packages that are not included in TeX Live and any other material that belongs to your manuscript.

**When you are asked to submit your manuscript source files, do the following if PDF version is restricted:**

* Select the Manuscript item type for .tex, .bbl, .bst, .sty, .bib, .cls, .nls, .ilg, and .nlo files.  
* Select the Figure item type for images and graphic files.  
* Select the Table item type for tables in .tex format.

Depending on the publication, Manuscript, Figure, or other item types may have different names.  
Do not upload LaTeX files as Supplemental items (under Supplementary material/Latex source file item type ).  
For step-by-step instructions, please refer [Submitting LaTeX Files to Editorial Manager](https://www.ariessys.com/wp-content/uploads/EM_PM_LaTeX_Guide.pdf)

### **Frequently asked questions**

Here we have answered some of the most common questions that arise at the point of submitting an article in LaTeX. If your question relates specifically to the Latex template, please contact elsarticle@stmdocs.in

## **FAQs**

### **Can I use subfolders in my TeX submission files?**

No. LaTeX submissions containing subfolders cannot be processed by EM. All submission files – including figures, tables, and style and bibliographic files – must be stored at the same folder level.

### **Can I use Overleaf (WriteLatex Ltd) to create my LaTeX manuscript and import it into EM?**

Yes, you can use Overleaf to create your LaTeX manuscript using TeX Live 2022\. When using Overleaf, please check the PDF carefully to ensure that the LaTeX file was compiled without any errors. Unlike EM, Overleaf generates a PDF even if compilation errors occurred – it does not stop at every error. In EM, however, compilation errors will generate an error log PDF only.

### **Which item types should I select for LaTeX submission files?**

Select the Manuscript item type for .tex, .bbl, .bst, .sty, .bib, .nls, .ilg, and .nlo files. Select the Figure item type for images and graphic files.  
Depending on the publication, Manuscript, Figure, or other item types may have different names. Contact our Support Team via the contact options at the bottom if you need clarification.

### **Why are my figures not appearing in the PDF?**

You may have stored your images in subfolders. EM cannot process LaTeX submissions in folders with a directory structure, so it cannot find files referenced in a different directory from the root.

### **Why does my PDF show question marks instead of bibliographic citations?**

If you have compiled your bibliography in a separate file and question marks appear in your PDF instead of the content in the associated bibliography file, your .tex manuscript file may contain incorrect formatting.  
For more information and support, see the [Elsevier Support Center](https://service.elsevier.com/app/answers/detail/a_id/36917/supporthub/publishing/kw/latex/)

## **Preparing CRC journal articles**

Camera-ready copy (CRC) journals are those that reproduce the author's manuscript exactly, with no intervention by the typesetter. Such journals are the exception rather than the rule; if a journal is CRC, this fact is clearly indicated in the instructions to authors. The [Procedia](https://www.elsevier.com/subject/procedia) series of journals, for example, are genuine CRC. Please read carefully the journal's instructions to authors.  
For LaTeX authors of camera-ready articles, we provide the ecrc.sty package. This is a small package designed to work with the elsarticle document class. All the features of elsarticle are available, along with a few extra commands specific to CRC reproduction. Documentation for the use of ecrc.sty is included in the manuscript template file available below.  
The archive file [elsarticle-ecrc.zip](https://assets.ctfassets.net/o78em1y1w4i4/3wVViBNFGDWZuMkfr1lXP9/13683569834330008c43fc585ed8ab2a/elsarticle-ecrc.zip) contains all the necessary files to run this package. To install ecrc.sty, unzip the elsarticle-ecrc.zip file. Usually the file can be unzipped directly in the local tree of your TeX distribution (for TeX Live, this would be in the texmf-local directory). The archive contains the following files:

* The elsarticle document class, [elsarticle.cls](https://assets.ctfassets.net/o78em1y1w4i4/UtkmcwzDXZeIUVlmhPGFm/4923f3c3bcc768b6fc4fa4f26cf39d72/elsarticle.cls)  
* The elsarticle documentation, [elsdoc.pdf](https://assets.ctfassets.net/o78em1y1w4i4/3ro3yQff1q67JHmLi1sAqV/1348e3852f277867230fc4b84a801734/elsdoc-1.pdf)  
* A BibTeX style file for the numbered reference style, [elsarticle-num.bst](https://assets.ctfassets.net/o78em1y1w4i4/3AcXXwb1xciwEveI37JmxA/606d2d3ffc7739fe2cb57b2c2eb169e0/elsarticle-num.bst) (other bibliographic styles are available (see above), but Elsevier CRC generally uses a numbered reference style)  
* The package file for Elsevier CRC, [ecrc.sty](https://assets.ctfassets.net/o78em1y1w4i4/4Z2HOgaByfB6xtELHcwwhx/5a202d88bf66f2dab38687c600808848/ecrc.sty)  
* Journal logo files [Elsevier-logo-3p.pdf](https://assets.ctfassets.net/o78em1y1w4i4/3ubcaE6PKedY0pzbelNA1t/ee84f4b9999339bbe1269d48297fc3de/elsevier-logo-3p.pdf) and [SDlogo-3p.pdf](https://assets.ctfassets.net/o78em1y1w4i4/1r6QE1mfxJmInEdwPucurb/3dbe13c369512a154e325a1d1c7996a6/SDlogo-3p.pdf) used to make the CRC article (when compiling with ***pdflatex***)  
* Alternative logo files [Elsevier-logo-3p.eps](https://assets.ctfassets.net/o78em1y1w4i4/6KmVc62xytgcyP0gw9lFlg/90e20b9474826a4cf21935bc49a01f4a/elsevier-logo-3p.eps) and [SDlogo-3p.eps](https://assets.ctfassets.net/o78em1y1w4i4/3GopE0Qqqk0HUReV7E7hxQ/48bd1030772b1438b280ed4e58d1816b/SDlogo-3p.ps) for use with ***latex***  
* A template manuscript file, [ecrc-template.tex](https://assets.ctfassets.net/o78em1y1w4i4/27zowmUKIvbiPUxbbnVFFK/4ca39b5f4d636af37e783f0625bd81f3/ecrc-template.tex)

Once the package has been installed, edit the manuscript file ecrc-template.tex according to the instructions in that file, and save with a new name. The manuscript file should be compiled with ***pdflatex*** (and ***bibtex*** if desired).  
Please only use these packages after confirmation from the journal's editors.

* [Nuclear and Particle Physics Proceedings](https://assets.ctfassets.net/o78em1y1w4i4/2GuyarpNiSgjlRBoLLLbKP/b74a1c5b3f8f557494e7b9ad330dbe0f/ecrc-nppp-p1.zip)  
* [Procedia Computer Science](https://assets.ctfassets.net/o78em1y1w4i4/1AaLwC4V4Yr1kGxJjR1vgb/0e6c53fd69777e0044a1c117ef184f8a/ecrc-procs.zip)


