"""Bundle only the image decoders that WriteOnSide exposes on Windows."""

hiddenimports = [
    "PIL.BmpImagePlugin",
    "PIL.GifImagePlugin",
    "PIL.IcoImagePlugin",
    "PIL.JpegImagePlugin",
    "PIL.PngImagePlugin",
    "PIL.TiffImagePlugin",
    "PIL.WebPImagePlugin",
]
