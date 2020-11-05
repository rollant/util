#!/usr/bin/python3
import sys
import os
import re
import logging
from pyexiv2 import Image
import argparse

log = logging.getLogger(__name__)


def parse_args():
    parser = argparse.ArgumentParser()
    parser.add_argument("file", type=str, nargs='+', help="Files to process")
    parser.add_argument("-c", action="store_true", help="Just clear caption")
    parser.add_argument("-n", action="store_true", help="Dry run mode")

    return parser.parse_args()


def get_keywords(img):
    meta = img.read_iptc()
    return meta.get('Iptc.Application2.Keywords', [])


def get_caption(img):
    caption = img.read_exif().get('Exif.Image.ImageDescription', '')
    print(caption)
    if caption:
        return caption

    caption = img.read_iptc().get('Iptc.Application2.Caption', '')
    if caption:
        return caption

    caption = img.read_xmp().get('Xmp.dc.description', '')
    caption = re.sub(r'^lang=".*?" ', '', caption)
    if caption:
        return caption

    # Return empty string if caption wasn't found
    return('')


def set_caption(img, caption, dry_run=False):
    exif_data = img.read_exif()
    exif_data['Exif.Image.ImageDescription'] = caption
    iptc_data = img.read_iptc()
    iptc_data['Iptc.Application2.Caption'] = caption
    xmp_data = img.read_xmp()
    xmp_data['Xmp.dc.description'] = caption
    if not dry_run:
        img.modify_exif(exif_data)
        img.modify_iptc(iptc_data)
        img.modify_xmp(xmp_data)


def process_image(filename, dry_run=False, clear_only=False):
    img = Image(filename)
    caption = ''
    if not clear_only:
        keywords = get_keywords(img)
        caption = '\n'.join(keywords)

    old_caption = get_caption(img)
    if caption != old_caption:
        # This way user can still see what's about to be done in dry run mode
        log.warning(f'{repr(old_caption)} -> {repr(caption)}')
        set_caption(img, caption, dry_run=dry_run)

    img.close()


if __name__ == '__main__':
    args = parse_args()
    for fn in args.file:
        process_image(fn, dry_run=args.n, clear_only=args.c)
