import base64
import logging
import re
import tempfile
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import Tuple

import pandas as pd
import pytesseract
from PIL import Image, ImageFont, ImageDraw
from bs4 import BeautifulSoup
from fontTools.ttLib import TTFont
from pytesseract import Output
from selenium.webdriver.common.by import By

"""
reverse engineer zhihu paid column dynamic font swapping mechanism
"""


def build_swapped_char_map(browser, flavor: str) -> dict[str, str]:
    if flavor == "paid_column":
        ## print swapped char to image and do OCR
        zhihu_font_file = save_dynamic_font_by_xpath(browser, r'//style[@type="text/css"]', Path(tempfile.gettempdir()))
        origin_char_list = parse_swapped_characters(Path(zhihu_font_file))
        test_image_file = generate_test_image(origin_char_list, Path(zhihu_font_file))
        target_char_list = apply_correction(ocr_swapped_char(test_image_file))
    elif flavor == "answer":
        ## analyze xml directly
        zhihu_font_file = save_dyanmic_font_brutal_force(browser, Path(tempfile.gettempdir()))
        #origin_char_list = parse_swapped_characters(Path(zhihu_font_file))
        #test_image_file = generate_test_image(origin_char_list, Path(zhihu_font_file))
        #target_char_list = apply_correction(ocr_swapped_char(test_image_file))
        origin_char_list, target_char_list = analyze_map_from_xml(zhihu_font_file)
    else:
        raise ValueError("unsupported flavor")

    origin_char_list = origin_char_list.replace(" ", "")
    target_char_list = target_char_list.replace(" ", "")

    sym_diff = set(origin_char_list).symmetric_difference(target_char_list)
    if len(sym_diff) > 0:
        print(f"original: {origin_char_list}")
        print(f"target:{target_char_list}")
        print(f"sym_diff: {sym_diff}, please update auto correction")
        logging.getLogger(__name__).error(f"{sym_diff}, please update auto correction")
        raise RuntimeError(f"{sym_diff}, please update auto correction")
    swapped_char_map = {origin: dest for (origin, dest) in zip(origin_char_list, target_char_list)}
    logging.getLogger(__name__).info(f"map built: {swapped_char_map}")
    return swapped_char_map


def save_dyanmic_font_brutal_force(browser, temp_path: Path) -> Path:
    soup = str(
        BeautifulSoup(
            "".join([x.get_attribute("outerHTML") for x in browser.find_elements(by=By.XPATH, value=r"//style")])
        )
    )
    soup_str = str(soup)
    start_idx = soup_str.find("base64,") + 7
    soup_str = soup_str[start_idx:]
    end_idx = soup_str.find(");")
    print(end_idx)
    font_decoded = base64.b64decode(soup_str[:end_idx])
    zhihu_font_file = temp_path / f'zhihufont_{pd.Timestamp.now().strftime("%Y%m%d_%H%M")}.ttf'
    with open(zhihu_font_file, "wb") as f:
        f.write(font_decoded)
    logging.getLogger(__name__).info(f"zhihu font downloaded to {zhihu_font_file}")
    return zhihu_font_file


## deprecated。 not work for answers, only work for paid column, using font_xpath = r'//style[@type="text/css"]'
def save_dynamic_font_by_xpath(browser, font_xpath: str, temp_path: Path) -> Path:
    es = browser.find_element(by=By.XPATH, value=font_xpath)
    font_html = es.get_attribute("innerHTML")
    fontbase64 = font_html.split("@font-face")[1]

    start_idx = fontbase64.find("base64") + 7
    end_idx = fontbase64.find(");")

    font_decoded = base64.b64decode(fontbase64[start_idx:end_idx])
    zhihu_font_file = temp_path / f'zhihufont_{pd.Timestamp.now().strftime("%Y%m%d_%H%M")}.ttf'
    with open(zhihu_font_file, "wb") as f:
        f.write(font_decoded)
    logging.getLogger(__name__).info(f"zhihu font downloaded to {zhihu_font_file}")
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


def analyze_map_from_xml(font_file: Path) -> Tuple[str, str]:
    zhihu_font = TTFont(font_file)
    font_xml = font_file.parent / f'{font_file.name.split(".")[0]}.xml'
    zhihu_font.saveXML(font_xml)
    root: ET.Element = ET.parse(font_xml).getroot()
    char_map = root.findall(".//cmap_format_4")[0]
    origin_list = [chr(int(element.get("code")[2:], 16)) for element in char_map.findall("map")]
    target_list = [chr(int(element.get("name")[3:], 16)) for element in char_map.findall("map")]
    radical_to_regular = pd.read_csv(Path(__file__).parent / "regular_radical_map.csv")
    radical_to_regular["radical"] = [chr(int(c[2:], 16)) for c in radical_to_regular["radical"]]
    radical_to_regular["regular"] = [chr(int(c[2:], 16)) for c in radical_to_regular["regular"]]
    radical_to_regular_map = {o: d for o, d in zip(radical_to_regular["radical"], radical_to_regular["regular"])}

    origin_list = "".join([radical_to_regular_map.get(c, c) for c in origin_list])
    target_list = "".join([radical_to_regular_map.get(c, c) for c in target_list])
    return origin_list, target_list


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
    logging.getLogger(__name__).info(f"test imaged file generated: {test_image_file}")
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
    correction_map = {"友": "发", "入": "人", "尝":"学", "鸭":"的"}
    return "".join([correction_map.get(c, c) for c in target_list])
