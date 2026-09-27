"""Converte um capítulo da dissertação (Markdown + LaTeX) para Word (.docx) em formato ABNT.

- Equações de destaque ($$ ... $$) viram equações nativas do Word, numeradas
  (N.1, N.2, ...) à direita; rótulos {#eq:nome} e referências {eq:nome} no texto são
  resolvidos para "(N.k)".
- Estilos: Times New Roman 12, espaçamento 1,5, recuo de 1,25 cm, texto justificado,
  margens 3/2 cm (A4); legendas acima de figuras e tabelas e fonte abaixo, em 10 pt.

Uso:  python scripts/gerar_docx.py docs/dissertacao/cap3_metodologia.md [--capitulo 3]
"""

import argparse
import re
import shutil
import tempfile
import zipfile
from pathlib import Path

import pypandoc

LARGURA_TEXTO = 9071  # A4 (11906) - margens de 3 cm e 2 cm, em twips


def preprocessar(md: str, capitulo: int) -> tuple[str, int]:
    """Numera as equações de destaque e resolve as referências {eq:nome}."""
    rotulos, n = {}, 0

    def numerar(m):
        nonlocal n
        n += 1
        if m.group(2):
            rotulos[m.group(2)] = f"({capitulo}.{n})"
        return m.group(1)

    md = re.sub(r"(\$\$\n.*?\n\$\$)[ \t]*(?:\{#(eq:[\w-]+)\})?", numerar, md, flags=re.S)
    faltando = set(re.findall(r"\{(eq:[\w-]+)\}", md)) - set(rotulos)
    if faltando:
        raise ValueError(f"Referências a equações sem rótulo: {sorted(faltando)}")
    md = re.sub(r"\{(eq:[\w-]+)\}", lambda m: rotulos[m.group(1)], md)
    return md, n


def numerar_equacoes(doc_xml: str, capitulo: int) -> str:
    """Coloca cada equação de destaque numa tabela sem bordas: equação | (N.k)."""
    k = 0

    def tabela(m):
        nonlocal k
        k += 1
        paragrafo = m.group(0)
        col1, col2 = LARGURA_TEXTO - 1000, 1000
        sem_borda = "".join(f'<w:{b} w:val="nil"/>' for b in
                            ("top", "left", "bottom", "right", "insideH", "insideV"))
        celula = ('<w:tc><w:tcPr><w:tcW w:w="{w}" w:type="dxa"/><w:vAlign w:val="center"/></w:tcPr>'
                  '{conteudo}</w:tc>')
        numero = (f'<w:p><w:pPr><w:pStyle w:val="NumeroEquacao"/></w:pPr>'
                  f'<w:r><w:t>({capitulo}.{k})</w:t></w:r></w:p>')
        return (f'<w:tbl><w:tblPr><w:tblW w:w="{LARGURA_TEXTO}" w:type="dxa"/>'
                f'<w:tblBorders>{sem_borda}</w:tblBorders><w:tblLayout w:type="fixed"/>'
                f'<w:tblCellMar><w:left w:w="0" w:type="dxa"/><w:right w:w="0" w:type="dxa"/></w:tblCellMar>'
                f'</w:tblPr><w:tblGrid><w:gridCol w:w="{col1}"/><w:gridCol w:w="{col2}"/></w:tblGrid>'
                f'<w:tr>{celula.format(w=col1, conteudo=paragrafo)}'
                f'{celula.format(w=col2, conteudo=numero)}</w:tr></w:tbl>')

    # Parágrafos que contêm apenas uma equação de destaque (m:oMathPara)
    return re.sub(r"<w:p>(?:(?!</w:p>).)*?<m:oMathPara>.*?</m:oMathPara>\s*</w:p>", tabela, doc_xml, flags=re.S), k


def _rpr(tam=24, negrito=False, italico=False):
    return ('<w:rPr><w:rFonts w:ascii="Times New Roman" w:hAnsi="Times New Roman" '
            'w:eastAsia="Times New Roman" w:cs="Times New Roman"/>'
            + ("<w:b/><w:bCs/>" if negrito else "") + ("<w:i/>" if italico else "")
            + '<w:color w:val="000000"/>'
            + f'<w:sz w:val="{tam}"/><w:szCs w:val="{tam}"/></w:rPr>')


def _estilo(sid, nome, ppr, rpr, base="Normal", heading=None):
    outline = f'<w:outlineLvl w:val="{heading}"/>' if heading is not None else ""
    nativo = sid in ("Normal", "BodyText", "Heading1", "Heading2", "Heading3")
    custom = "" if nativo else ' w:customStyle="1"'
    padrao = ' w:default="1"' if sid == "Normal" else ""
    basedon = f'<w:basedOn w:val="{base}"/>' if base else ""
    return (f'<w:style w:type="paragraph"{padrao}{custom} w:styleId="{sid}"><w:name w:val="{nome}"/>'
            f'{basedon}<w:qFormat/><w:pPr>{ppr}{outline}</w:pPr>{rpr}</w:style>')


def estilos_abnt(styles_xml: str) -> str:
    esp15 = '<w:spacing w:before="0" w:after="0" w:line="360" w:lineRule="auto"/>'
    esp1 = '<w:spacing w:before="0" w:after="0" w:line="240" w:lineRule="auto"/>'
    corpo = f'{esp15}<w:ind w:firstLine="709"/><w:jc w:val="both"/>'
    novos = {
        "Normal": _estilo("Normal", "Normal", corpo, _rpr(), base=""),
        "BodyText": _estilo("BodyText", "Body Text", corpo, _rpr()),
        "FirstParagraph": _estilo("FirstParagraph", "First Paragraph", corpo, _rpr(), base="BodyText"),
        "Compact": _estilo("Compact", "Compact", f'{esp1}<w:ind w:firstLine="0"/><w:jc w:val="left"/>', _rpr(20)),
        "Heading1": _estilo("Heading1", "heading 1", f'<w:keepNext/><w:spacing w:before="0" w:after="360" '
                            f'w:line="360" w:lineRule="auto"/><w:ind w:firstLine="0"/><w:jc w:val="left"/>',
                            _rpr(24, negrito=True), heading=0),
        "Heading2": _estilo("Heading2", "heading 2", f'<w:keepNext/><w:spacing w:before="360" w:after="240" '
                            f'w:line="360" w:lineRule="auto"/><w:ind w:firstLine="0"/><w:jc w:val="left"/>',
                            _rpr(24, negrito=True), heading=1),
        "Heading3": _estilo("Heading3", "heading 3", f'<w:keepNext/><w:spacing w:before="240" w:after="240" '
                            f'w:line="360" w:lineRule="auto"/><w:ind w:firstLine="0"/><w:jc w:val="left"/>',
                            _rpr(24), heading=2),
        "Legenda": _estilo("Legenda", "Legenda", f'<w:keepNext/><w:spacing w:before="240" w:after="60" '
                           f'w:line="240" w:lineRule="auto"/><w:ind w:firstLine="0"/><w:jc w:val="center"/>',
                           _rpr(20)),
        "Figura": _estilo("Figura", "Figura", f'<w:keepNext/>{esp1}<w:ind w:firstLine="0"/><w:jc w:val="center"/>',
                          _rpr(20)),
        "Fonte": _estilo("Fonte", "Fonte", f'<w:spacing w:before="60" w:after="240" w:line="240" '
                         f'w:lineRule="auto"/><w:ind w:firstLine="0"/><w:jc w:val="center"/>', _rpr(20)),
        "Referencia": _estilo("Referencia", "Referencia", f'<w:spacing w:before="0" w:after="240" '
                              f'w:line="240" w:lineRule="auto"/><w:ind w:firstLine="0"/><w:jc w:val="left"/>',
                              _rpr(24)),
        "NumeroEquacao": _estilo("NumeroEquacao", "Numero Equacao", f'{esp1}<w:ind w:firstLine="0"/>'
                                 f'<w:jc w:val="right"/>', _rpr(24)),
    }
    for sid in novos:
        styles_xml = re.sub(rf'<w:style [^>]*w:styleId="{sid}"[^>]*>.*?</w:style>', "", styles_xml, flags=re.S)
    return styles_xml.replace("</w:styles>", "".join(novos.values()) + "</w:styles>")


def pagina_a4(doc_xml: str) -> str:
    sect = ('<w:sectPr><w:pgSz w:w="11906" w:h="16838"/>'
            '<w:pgMar w:top="1701" w:right="1134" w:bottom="1134" w:left="1701" '
            'w:header="709" w:footer="709" w:gutter="0"/></w:sectPr>')
    doc_xml = re.sub(r"<w:sectPr[ >].*?</w:sectPr>", "", doc_xml, flags=re.S)
    return doc_xml.replace("</w:body>", sect + "</w:body>")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("entrada")
    ap.add_argument("--capitulo", type=int, default=3)
    ap.add_argument("--saida")
    args = ap.parse_args()

    entrada = Path(args.entrada).resolve()
    saida = Path(args.saida) if args.saida else entrada.with_suffix(".docx")
    md, n_eq = preprocessar(entrada.read_text(encoding="utf-8"), args.capitulo)

    with tempfile.TemporaryDirectory() as tmp:
        bruto = Path(tmp) / "bruto.docx"
        pypandoc.convert_text(md, "docx", format="markdown", outputfile=str(bruto),
                              extra_args=[f"--resource-path={entrada.parent}"])
        pasta = Path(tmp) / "x"
        with zipfile.ZipFile(bruto) as z:
            z.extractall(pasta)
        doc = (pasta / "word" / "document.xml").read_text(encoding="utf-8")
        # m:nor (texto normal) e m:sty são mutuamente exclusivos no esquema OMML
        doc = re.sub(r"(<m:nor ?/>)\s*<m:sty [^>]*/>", r"\1", doc)
        doc, k = numerar_equacoes(doc, args.capitulo)
        if k != n_eq:
            raise RuntimeError(f"{n_eq} equações no texto, mas {k} encontradas no .docx")
        (pasta / "word" / "document.xml").write_text(pagina_a4(doc), encoding="utf-8")
        est = pasta / "word" / "styles.xml"
        est.write_text(estilos_abnt(est.read_text(encoding="utf-8")), encoding="utf-8")
        ct = pasta / "[Content_Types].xml"
        tipos = ct.read_text(encoding="utf-8")
        if 'Extension="png"' not in tipos:
            tipos = tipos.replace("<Default ", '<Default Extension="png" ContentType="image/png"/><Default ', 1)
            ct.write_text(tipos, encoding="utf-8")
        saida.unlink(missing_ok=True)
        shutil.make_archive(str(saida.with_suffix("")), "zip", pasta)
        Path(str(saida.with_suffix("")) + ".zip").rename(saida)
    print(f"{saida}  ({n_eq} equações numeradas)")


if __name__ == "__main__":
    main()
