"""
read_table8_checkmarks.py
Lit le tableau "Droits d'acces et visibilite" (§4.8) des specs EVER v1.1/v1.2.

Piege : Nicolas coche les cases avec des symboles Wingdings (w:sym char="F0FC",
un caractere de police, pas du texte) plutot qu'avec du texte. Une extraction
naive via cell.text (pandoc, python-docx .text) renvoie une cellule VIDE meme
quand une coche est presente a l'oeil dans Word.

Usage :
  python scripts/read_table8_checkmarks.py "chemin\\vers\\le\\docx"
"""
import sys
from docx import Document
from docx.oxml.ns import qn

DEFAULT_PATH = r'C:\Users\y_bicrel\Downloads\EVER_2026_Site_Suivi_Affectation_20260820.docx'


def main():
    path = sys.argv[1] if len(sys.argv) > 1 else DEFAULT_PATH
    doc = Document(path)

    for t in doc.tables:
        if t.rows[0].cells[0].text.strip() != 'Fonctionnalité':
            continue
        headers = [c.text.strip() for c in t.rows[0].cells]
        print('Colonnes :', headers)
        for r in t.rows[1:]:
            row_label = r.cells[0].text.strip()
            marks = []
            for c in r.cells[1:]:
                syms = c._tc.findall('.//' + qn('w:sym'))
                has_check = any(s.get(qn('w:char')) == 'F0FC' for s in syms)
                marks.append('X' if has_check else ('txt:' + c.text.strip() if c.text.strip() else '-'))
            print(f'  {row_label:30s} : ' + ' | '.join(marks))
        return

    print('Tableau des droits non trouve (recherche par en-tete "Fonctionnalité").')


if __name__ == '__main__':
    main()
