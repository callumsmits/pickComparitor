#pickComparitor - manually curate particles after automatic unpicking
This script provides a convenient way to analyse and curate the results of unpicking. When run the gui interface allows you to easily view kept and discarded picks for each image in a dataset, and restore particles or unpick more.

##Installation
###Prerequisites
- [Numpy](http://www.numpy.org/)
- [scikit-image](http://scikit-image.org/)
- [PyQt4](https://www.riverbankcomputing.com/software/pyqt/download)
- [qimage2ndarray](https://github.com/hmeine/qimage2ndarray)

Just clone this repository and check that the script pickComparitor.py is exectutable (and perhaps in your path).

##Usage
The script is run from the command line from your RELION project directory and running without arguments shows the expected input:
```
$ pickComparitor.py 

Usage: pickComparitor.py starFileName newPickRoot originalPickRoot boxsize sigmaContrast scale
```
where the starFileName is a star file containing a list of micrograph names (perhaps all_micrographs.star or all_micrographs_ctf.star), newPickRoot is the extension used during unpicking, originalPickRoot is the extension from autopicking, boxsize is the particle diameter in pixels, sigmaContrast is the image contrast as calculated in RELION and scale is the scale factor used to display each image on the display. As an example:
```
$ pickComparitor.py all_micrographs.star _autopick_unpick.star _autopick.star 200 3.0 0.2
```
