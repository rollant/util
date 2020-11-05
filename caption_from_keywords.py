#!/usr/bin/python3
import sys
import os
import re
import logging
import pyexiv2
import argparse
import subprocess

log = logging.getLogger(__name__)


def parse_args():
    parser = argparse.ArgumentParser()
    parser.add_argument("file", type=str, nargs='+', help="Files to process")
    parser.add_argument("-c", action="store_true", help="Just clear caption")
    parser.add_argument("-n", action="store_true", help="Dry run mode")
    parser.add_argument("-w", action="store_true",
                        help="Translate Windows filenames (requires wslpath)")

    return parser.parse_args()


# This tool is intended to be run from CaptureOne on Windows via WSL.
# C1 supplies Windows path that must be translated to WSL path
# (i. e. d:\Photos\test.jpg becomes /mnt/d/Photos/test.jpg)
def translate_filename(win_fn):
    win_fn = re.sub(r'(^"|"$)', '', win_fn)
    try:
        out = subprocess.run(["wslpath", win_fn], capture_output=True,
                             encoding="utf-8", check=True)
        fn = out.stdout.rstrip()
        return fn
    except subprocess.CalledProcessError as e:
        log.error(f"wslpath error: {e.stderr}")
        raise


def get_keywords(meta):
    for tag_name in ['Iptc.Application2.Keywords', 'Xmp.dc.subject']:
        tag = meta.get(tag_name, None)
        if tag is not None:
            return tag.value
    return []


def get_exif_caption(meta):
    tag = meta.get('Exif.Image.ImageDescription', None)
    if tag is not None:
        if tag.value:
            return tag.value


def get_iptc_caption(meta):
    tag = meta.get('Iptc.Application2.Caption', None)
    if tag is not None:
        if tag.value:
            # This tag is not repeatable, hence there's always
            # one element in the list
            return tag.value[0]


def get_xmp_caption(meta):
    tag = meta.get('Xmp.dc.description', None)
    if tag is not None:
        tag_value = tag.value
        if 'x-default' in tag_value.keys():
            return tag_value['x-default']
        else:
            lang = tag_value.keys()[0]
            return tag_value[lang]


def get_caption(meta):
    for func in [get_exif_caption, get_iptc_caption, get_xmp_caption]:
        caption = func(meta)
        if caption:
            return caption
    return('')


def set_caption(meta, caption, dry_run=False):
    meta['Exif.Image.ImageDescription'] = caption
    meta['Iptc.Application2.Caption'] = [caption]
    meta['Xmp.dc.description'] = {'x-default': caption}
    if not dry_run:
        meta.write()


def process_image(filename, dry_run=False, clear_only=False):
    meta = pyexiv2.ImageMetadata(filename)
    meta.read()
    caption = ''
    if not clear_only:
        keywords = get_keywords(meta)
        caption = '\n'.join(keywords)

    old_caption = get_caption(meta)
    if caption != old_caption:
        # This way user can still see what's about to be done in dry run mode
        short_name = os.path.basename(filename)
        log.warning(f'{short_name}: {repr(old_caption)} -> {repr(caption)}')
        set_caption(meta, caption, dry_run=dry_run)


if __name__ == '__main__':
    args = parse_args()
    for fn in args.file:
        if args.w:
            fn = translate_filename(fn)
        process_image(fn, dry_run=args.n, clear_only=args.c)
