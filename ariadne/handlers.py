import numpy
from PIL import Image

class BMM_JPEG_HANDLER:
    def __init__(self, resource_path):
        # resource_path is really a template string with a %d in it
        self._template = resource_path

    def __call__(self, index):
        filepath = self._template % index
        return numpy.asarray(Image.open(filepath))
