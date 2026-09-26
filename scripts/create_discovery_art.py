"""Generate nine simple original editorial SVG scenes for the prototype."""
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1] / 'frontend' / 'public' / 'discovery-art'
ROOT.mkdir(parents=True, exist_ok=True)

SCENES = {
    'curiosity-a': ('#e9e4f6', '#a9b9b2', '''<rect x="215" y="136" width="276" height="275" rx="16" fill="#fff9f1" stroke="#65517b" stroke-width="11"/><rect x="271" y="191" width="163" height="129" fill="#bad5d6" stroke="#65517b" stroke-width="10"/><path d="M352 191v129m-81-67h163" stroke="#65517b" stroke-width="8"/><path d="M500 280q-65 8-52 79" stroke="#e2767e" stroke-width="23" fill="none"/><ellipse cx="344" cy="397" rx="92" ry="24" fill="#927199"/><path d="M310 364h72l-15 35h-40Z" fill="#d66f71"/>'''),
    'curiosity-b': ('#eee5f6', '#f4ca9d', '''<path d="M242 260q25-115 110-115t106 115Z" fill="#e8a5a1" stroke="#684f80" stroke-width="11"/><path d="M260 261h190" stroke="#684f80" stroke-width="10"/><path d="M352 265v121" stroke="#684f80" stroke-width="16"/><ellipse cx="352" cy="403" rx="112" ry="16" fill="#684f80"/><path d="M482 230q70-8 71 67" stroke="#f8f5ed" stroke-width="23" fill="none" stroke-linecap="round"/><circle cx="561" cy="305" r="17" fill="#ea6b74"/>'''),
    'curiosity-c': ('#e9e1f5', '#b6c6ac', '''<path d="M185 418V212q165-115 330 0v206Z" fill="#f8efea" stroke="#65517b" stroke-width="14"/><path d="M259 417V224q87-54 173 0v193Z" fill="#ae7181" stroke="#65517b" stroke-width="10"/><circle cx="407" cy="326" r="11" fill="#fff2c6"/><path d="M518 408q20-100 54-83m-45 75q22-70 54-52" fill="none" stroke="#8eae94" stroke-width="16" stroke-linecap="round"/><circle cx="569" cy="322" r="16" fill="#ed8b8f"/>'''),
    'uncertainty-a': ('#eee5f6', '#b8bad7', '''<rect x="264" y="92" width="181" height="329" rx="30" fill="#5c5075"/><rect x="277" y="119" width="154" height="252" rx="9" fill="#fcf8ed"/><path d="M301 183h97m-97 34h61" stroke="#b8a9ca" stroke-width="12" stroke-linecap="round"/><circle cx="353" cy="394" r="11" fill="#ddd0e1"/><path d="M479 156h102v78H528l-30 30v-30h-19Z" fill="#e5adb0"/><path d="M518 190h26" stroke="#fff" stroke-width="9" stroke-linecap="round"/>'''),
    'uncertainty-b': ('#f1e7f4', '#c9b8a0', '''<path d="M189 322h323l37 60H166Z" fill="#b36e7c" stroke="#634c70" stroke-width="9"/><path d="M255 322l34-87h132l43 87" fill="#e7a9a0" stroke="#634c70" stroke-width="9"/><circle cx="242" cy="383" r="36" fill="#5d516d"/><circle cx="463" cy="383" r="36" fill="#5d516d"/><circle cx="242" cy="383" r="14" fill="#efdecd"/><circle cx="463" cy="383" r="14" fill="#efdecd"/><path d="M179 246h62m238 0h58" stroke="#907aa3" stroke-width="12" stroke-linecap="round"/>'''),
    'uncertainty-c': ('#eee5f7', '#d9b4b2', '''<path d="M184 164h251a33 33 0 0 1 33 33v110a33 33 0 0 1-33 33H317l-55 55v-55h-78a33 33 0 0 1-33-33V197a33 33 0 0 1 33-33Z" fill="#fffaf0" stroke="#6f5a83" stroke-width="10"/><circle cx="244" cy="252" r="13" fill="#a48eb7"/><circle cx="309" cy="252" r="13" fill="#a48eb7"/><circle cx="374" cy="252" r="13" fill="#a48eb7"/><path d="M491 193h70m-54 37h66" stroke="#e18991" stroke-width="15" stroke-linecap="round"/>'''),
    'imagination-a': ('#eee5fa', '#efd5ba', '''<path d="M193 422V233q155-126 314 0v189Z" fill="#fff7ee" stroke="#665082" stroke-width="10"/><path d="M175 238q165-166 348 0" fill="none" stroke="#745b95" stroke-width="43" stroke-linecap="round"/><path d="M330 422v-105q36-47 75 0v105" fill="#e9bbca" stroke="#665082" stroke-width="8"/><path d="M252 279l10 21 22 3-17 16 4 22-19-11-19 11 4-22-17-16 22-3Zm201 0 10 21 22 3-17 16 4 22-19-11-19 11 4-22-17-16 22-3Z" fill="#f0bf76"/>'''),
    'imagination-b': ('#eae4f6', '#c6d9ca', '''<rect x="206" y="175" width="295" height="227" rx="27" fill="#fffaf0" stroke="#65517c" stroke-width="12"/><circle cx="291" cy="272" r="33" fill="#e6879b"/><circle cx="352" cy="272" r="33" fill="#dbb674"/><circle cx="413" cy="272" r="33" fill="#9dbbab"/><path d="M252 354h204" stroke="#b8a8cc" stroke-width="12" stroke-linecap="round"/><path d="M354 174v-53m-25 2 25-25 25 25" fill="none" stroke="#65517c" stroke-width="10" stroke-linecap="round"/>'''),
    'imagination-c': ('#e7e5f9', '#aacdc2', '''<path d="M80 394q180-78 270-6t270 0v132H80Z" fill="#a4c9c7"/><path d="M179 388q20-172 166-191 138-5 177 191" fill="#b9bf9c"/><path d="M350 338V189m-75 112q66-109 75-111m0 0q19 15 72 111" stroke="#716087" stroke-width="16" stroke-linecap="round" fill="none"/><circle cx="284" cy="243" r="20" fill="#fff2c9"/><circle cx="416" cy="262" r="17" fill="#fff2c9"/><path d="M241 420q66 30 137 2t142 0" fill="none" stroke="#fff3ec" stroke-width="12" stroke-linecap="round"/>'''),
}

for name, (background, land, art) in SCENES.items():
    svg = (f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 700 520">'
           f'<rect width="700" height="520" fill="{background}"/>'
           f'<circle cx="562" cy="96" r="75" fill="#fff" opacity=".56"/>'
           f'<path d="M0 387q180-34 350 0t350 0v133H0Z" fill="{land}"/>'
           f'{art}</svg>')
    (ROOT / f'{name}.svg').write_text(svg, encoding='utf-8')
print(f'{len(SCENES)} Discovery branch illustrations ready')
