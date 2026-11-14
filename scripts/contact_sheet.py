"""Tile preview stills into one contact sheet: contact_sheet.py out.jpg in1 in2 ..."""
import sys
import cv2
import numpy as np

out, files = sys.argv[1], sys.argv[2:]
tiles = []
for f in files:
    im = cv2.imread(f)
    h, w = im.shape[:2]
    s = 640 / max(w, h) if w > h else 360 / h
    im = cv2.resize(im, (int(w * s), int(h * s)), interpolation=cv2.INTER_AREA)
    cv2.putText(im, f.split("_")[-1][:-4], (8, 24), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 2)
    tiles.append(im)
cols = 3 if tiles[0].shape[1] > tiles[0].shape[0] else 5
th, tw = tiles[0].shape[:2]
rows = (len(tiles) + cols - 1) // cols
sheet = np.zeros((rows * th, cols * tw, 3), np.uint8)
for i, im in enumerate(tiles):
    r, c = divmod(i, cols)
    sheet[r * th:r * th + im.shape[0], c * tw:c * tw + im.shape[1]] = im
cv2.imwrite(out, sheet, [cv2.IMWRITE_JPEG_QUALITY, 90])
