#! env python3
# The Mia! Accounting Project.
# Author: imacat@mail.imacat.idv.tw (imacat), 2023/1/28

#  Copyright (c) 2023 imacat.
#
#  Licensed under the Apache License, Version 2.0 (the "License");
#  you may not use this file except in compliance with the License.
#  You may obtain a copy of the License at
#
#      http://www.apache.org/licenses/LICENSE-2.0
#
#  Unless required by applicable law or agreed to in writing, software
#  distributed under the License is distributed on an "AS IS" BASIS,
#  WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#  See the License for the specific language governing permissions and
#  limitations under the License.
"""The translation management utilities for the test site.

"""
import os
import re
from pathlib import Path
from time import strftime

import click
from babel.messages.frontend import CommandLineInterface
from opencc import OpenCC

root_dir: Path = Path(__file__).parent.parent
translation_dir: Path = root_dir / "tests" / "test_site" / "translations"
domain: str = "messages"


@click.group()
def main() -> None:
    """Manages the message translation."""


@click.command("extract")
def babel_extract() -> None:
    """Extracts the messages for translation."""
    os.chdir(root_dir)
    cfg: Path = translation_dir / "babel.cfg"
    pot: Path = translation_dir / f"{domain}.pot"
    zh_hant: Path = translation_dir / "zh_Hant" / "LC_MESSAGES"\
        / f"{domain}.po"
    zh_hans: Path = translation_dir / "zh_Hans" / "LC_MESSAGES"\
        / f"{domain}.po"
    CommandLineInterface().run([
        "pybabel", "extract", "-F", str(cfg), "-k", "lazy_gettext", "-k", "A_",
        "-o", str(pot), str(Path("tests") / "test_site")])
    if not zh_hant.exists():
        zh_hant.touch()
    if not zh_hans.exists():
        zh_hans.touch()
    CommandLineInterface().run([
        "pybabel", "update", "-i", str(pot), "-D", domain,
        "-d", translation_dir])


@click.command("compile")
def babel_compile() -> None:
    """Compiles the translated messages."""
    __convert_chinese()
    __update_rev_date()
    CommandLineInterface().run([
        "pybabel", "compile", "-D", domain, "-d", translation_dir])


def __convert_chinese() -> None:
    """Updates the Simplified Chinese translation according to the Traditional
    Chinese translation.

    :return: None.
    """
    cc: OpenCC = OpenCC("tw2sp")
    zh_hant: Path = translation_dir / "zh_Hant" / "LC_MESSAGES"\
        / f"{domain}.po"
    zh_hans: Path = translation_dir / "zh_Hans" / "LC_MESSAGES"\
        / f"{domain}.po"
    now: str = strftime("%Y-%m-%d %H:%M%z")
    with open(zh_hant, "r") as f:
        content: str = f.read()
    content = cc.convert(content)
    content = re.sub(r"^# Chinese \\(Traditional\\) translations ",
                     "# Chinese (Simplified) translations ", content)
    content = re.sub(r"\n\"PO-Revision-Date: [^\n]*\"\n",
                     f"\n\"PO-Revision-Date: {now}\\\\n\"\n",
                     content)
    content = content.replace("\n\"Language-Team: zh_Hant",
                              "\n\"Language-Team: zh_Hans")
    content = content.replace("\n\"Language: zh_Hant\\n\"\n",
                              "\n\"Language: zh_Hans\\n\"\n")
    content = content.replace("\nmsgstr \"zh-Hant\"\n",
                              "\nmsgstr \"zh-Hans\"\n")
    zh_hans.parent.mkdir(exist_ok=True)
    with open(zh_hans, "w") as f:
        f.write(content)


def __update_rev_date() -> None:
    """Updates the revision dates in the PO files.

    :return: None.
    """
    for language_dir in translation_dir.glob("*"):
        po_file: Path = language_dir / "LC_MESSAGES" / f"{domain}.po"
        if po_file.is_file():
            __update_file_rev_date(po_file)


def __update_file_rev_date(file: Path) -> None:
    """Updates the revision date of a PO file

    :param file: The PO file.
    :return: None.
    """
    now = strftime("%Y-%m-%d %H:%M%z")
    with open(file, "r+") as f:
        content = f.read()
        content = re.sub(r"\n\"PO-Revision-Date: [^\n]*\"\n",
                         f"\n\"PO-Revision-Date: {now}\\\\n\"\n",
                         content)
        f.seek(0)
        f.write(content)


main.add_command(babel_extract)
main.add_command(babel_compile)

if __name__ == '__main__':
    main()
