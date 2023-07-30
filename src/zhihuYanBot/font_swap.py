import base64
import logging
import re
import tempfile
import xml.etree.ElementTree as ET
from pathlib import Path

import pandas as pd
import pytesseract
from PIL import Image, ImageFont, ImageDraw
from fontTools.ttLib import TTFont
from pytesseract import Output
from selenium.webdriver.common.by import By

"""
reverse engineer zhihu paid column dynamic font swapping mechanism
"""

def build_swapped_char_map(browser) -> dict[str, str]:
    zhihu_font_file = save_dynamic_font(browser, Path(tempfile.gettempdir()))
    origin_char_list = parse_swapped_characters(Path(zhihu_font_file))
    test_image_file = generate_test_image(origin_char_list, Path(zhihu_font_file))
    target_char_list = apply_correction(ocr_swapped_char(test_image_file))
    sym_diff = set(origin_char_list).symmetric_difference(target_char_list)
    if len(sym_diff) > 0:
        logging.error(f"{sym_diff}, please update auto correction")
        raise RuntimeError(f"{sym_diff}, please update auto correction")
    swapped_char_map = {origin: dest for (origin, dest) in zip(origin_char_list, target_char_list)}
    logging.info(f"map built: {swapped_char_map}")
    return swapped_char_map


def save_dynamic_font(browser, temp_path: Path) -> Path:
    es = browser.find_element(by=By.XPATH, value=r'//style[@type="text/css"]')
    font_html = es.get_attribute("innerHTML")
    fontbase64 = font_html.split("@font-face")[1]
    start_idx = fontbase64.find("base64") + 7
    end_idx = fontbase64.find(")\n")

    font_decoded = base64.b64decode(fontbase64[start_idx:end_idx])
    zhihu_font_file = temp_path / f'zhihufont_{pd.Timestamp.now().strftime("%Y%m%d_%H%M")}.ttf'
    with open(zhihu_font_file, "wb") as f:
        f.write(font_decoded)
    logging.info(f"zhihu font downloaded to {zhihu_font_file}")
    return zhihu_font_file


def parse_swapped_characters(font_file: Path) -> str:
    zhihu_font = TTFont(font_file)
    font_xml = font_file.parent / f'{font_file.name.split(".")[0]}.xml'
    zhihu_font.saveXML(font_xml)
    root: ET.Element = ET.parse(font_xml).getroot()
    chars = root.findall(".//TTGlyph")
    char_list = []
    for char in chars:
        this_unicode = char.get("name")[3:]
        if re.match("[0-9][A-Za-z0-9]{3}", this_unicode):
            char_list.append(chr(int(this_unicode, 16)))
    return "".join(char_list)


def generate_test_image(char_list: str, swapped_font_file: Path) -> Path:
    N = len(char_list)
    font_size = 128
    persize = font_size
    img = Image.new("RGB", (N * persize, persize))
    draw = ImageDraw.Draw(img)
    zhihu_img_font = ImageFont.truetype(str(swapped_font_file.resolve()), size=font_size)
    for idx, char in enumerate(char_list):
        draw.text((idx * font_size, 0), char, font=zhihu_img_font)
    test_image_file = swapped_font_file.parent / f'{swapped_font_file.name.split(".")[0]}.jpg'
    img.save(str(test_image_file.resolve()))
    logging.info(f"test imaged file generated: {test_image_file}")
    return test_image_file


def ocr_swapped_char(test_image: Path) -> str:
    text = pytesseract.image_to_string(
        str(test_image.resolve()),
        lang="chi_sim",
        config="-c preserve_interword_spaces=1 --psm 6",
        output_type=Output.BYTES,
    ).decode("utf-8")
    return text[:-1]


def apply_correction(target_list: str) -> str:
    correction_map = {"友": "发", "入": "人"}
    return "".join([correction_map.get(c, c) for c in target_list])
