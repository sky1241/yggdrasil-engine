"""Inject sourced t=0 origins for all 19 Level 0 concepts."""
import json

ORIGINS_FILE = "c:/Users/ludov/Desktop/ygg/yggdrasil-engine/data/scan/origins_to_source.json"

L0_SOURCES = {
    "Art": {
        "real_t0": -45500,
        "real_t0_event": "Sulawesi cave paintings (warty pig, Leang Tedongnge) -- oldest figurative art",
        "real_t0_source": "Brumm A. et al. (2021) Science Advances 7(3):eabd4648, DOI:10.1126/sciadv.abd4648; Aubert M. et al. (2024) Nature 631:105-110, DOI:10.1038/s41586-024-07541-7"
    },
    "Biology": {
        "real_t0": -344,
        "real_t0_event": "Aristotle, Historia Animalium -- first systematic comparative zoology (~540 species)",
        "real_t0_source": "Mayr E. (1982) The Growth of Biological Thought, Harvard UP, Ch.4 p.87; Lennox J.G. (2001) Aristotle's Philosophy of Biology, Cambridge UP"
    },
    "Business": {
        "real_t0": -3100,
        "real_t0_event": "Sumerian cuneiform accounting tablets, Uruk IV -- writing invented for business",
        "real_t0_source": "Nissen H.J., Damerow P., Englund R.K. (1993) Archaic Bookkeeping, U. Chicago Press, ISBN:978-0226586595"
    },
    "Chemistry": {
        "real_t0": 300,
        "real_t0_event": "Zosimos of Panopolis, Cheirokmeta + Papyrus Leiden/Stockholm -- first alchemical theory + planetary metal symbols",
        "real_t0_source": "Principe L.M. (2013) The Secrets of Alchemy, U. Chicago Press, ISBN:978-0226682952; Wentrup C. (2024) ChemPlusChem, DOI:10.1002/cplu.202400033"
    },
    "Computer science": {
        "real_t0": 1936,
        "real_t0_event": "ANACHRONISM at 1000 CE. Turing, On Computable Numbers -- Turing machine, foundation of CS",
        "real_t0_source": "Turing A.M. (1936) Proc. London Math. Soc. s2-42(1):230-265, DOI:10.1112/plms/s2-42.1.230"
    },
    "Economics": {
        "real_t0": -362,
        "real_t0_event": "Xenophon, Oikonomikos -- first systematic economic theory, coined oikonomia",
        "real_t0_source": "Lowry S.T. (1987) The Archaeology of Economic Ideas, Duke UP, ISBN:978-0822307198; Finley M.I. (1970) Past & Present 47:3-25, DOI:10.1093/past/47.1.3"
    },
    "Engineering": {
        "real_t0": -2650,
        "real_t0_event": "Imhotep, Step Pyramid of Djoser at Saqqara -- first named engineer, first monumental stone construction",
        "real_t0_source": "Lauer J.-P. (1976) Saqqara, Thames & Hudson; Romer J. (2007) The Great Pyramid, Cambridge UP, ISBN:978-0521871662"
    },
    "Environmental science": {
        "real_t0": 1864,
        "real_t0_event": "Marsh, Man and Nature -- first systematic study of human environmental impact",
        "real_t0_source": "Lowenthal D. (2000) George Perkins Marsh: Prophet of Conservation, U. Washington Press, ISBN:978-0295979090"
    },
    "Geography": {
        "real_t0": -240,
        "real_t0_event": "Eratosthenes coins geographia, writes Geographika + measures Earth circumference",
        "real_t0_source": "Livingstone D.N. (1992) The Geographical Tradition, Blackwell, Ch.2; Roller D.W. (2010) Eratosthenes' Geography, Princeton UP"
    },
    "Geology": {
        "real_t0": 1669,
        "real_t0_event": "Steno, Prodromus -- laws of superposition/horizontality/continuity, founding stratigraphy",
        "real_t0_source": "Laudan R. (1987) From Mineralogy to Geology, U. Chicago Press, Ch.2; Rudwick M.J.S. (1985) The Meaning of Fossils, U. Chicago Press"
    },
    "History": {
        "real_t0": -440,
        "real_t0_event": "Herodotus, Historiai -- first systematic historical inquiry with critical method",
        "real_t0_source": "Momigliano A. (1958) History 43(147):1-13, DOI:10.1111/j.1468-229X.1958.tb02036.x"
    },
    "Materials science": {
        "real_t0": -3300,
        "real_t0_event": "Bronze Age -- first deliberate alloying (copper + tin), birth of materials engineering",
        "real_t0_source": "Roberts B.W. et al. (2009) Antiquity 83(322):1012-1022, DOI:10.1017/S0003598X00099312; Cahn R.W. (2001) The Coming of Materials Science, Pergamon"
    },
    "Mathematics": {
        "real_t0": -43000,
        "real_t0_event": "Lebombo bone -- 29 tally notches on baboon fibula, Border Cave, eSwatini",
        "real_t0_source": "d'Errico F. et al. (2012) PNAS 109(33):13214-13219, DOI:10.1073/pnas.1204213109; Bogoshi J. et al. (1987) Mathematical Gazette 71(458):294"
    },
    "Medicine": {
        "real_t0": -2500,
        "real_t0_event": "Edwin Smith Papyrus (original composition) -- 48-case surgical treatise, rational diagnosis protocol",
        "real_t0_source": "Breasted J.H. (1930) The Edwin Smith Surgical Papyrus, U. Chicago OI Pubs 3-4; Sanchez G.M. & Burridge A.L. (2007) Neurosurgical Focus 23(1):E5, DOI:10.3171/FOC-07/07/E5"
    },
    "Philosophy": {
        "real_t0": -585,
        "real_t0_event": "Thales of Miletus -- first naturalistic explanation (water-as-arche), eclipse prediction",
        "real_t0_source": "Guthrie W.K.C. (1962) A History of Greek Philosophy Vol I, Cambridge UP, Ch.2 pp.45-72, ISBN:978-0-521-29420-1"
    },
    "Physics": {
        "real_t0": -350,
        "real_t0_event": "Aristotle, Physica (8 books) -- first systematic natural philosophy, defines motion/causation/time",
        "real_t0_source": "Grant E. (2007) A History of Natural Philosophy, Cambridge UP, DOI:10.1017/CBO9780511999000; Lindberg D.C. (2007) Beginnings of Western Science, U. Chicago Press"
    },
    "Political science": {
        "real_t0": -350,
        "real_t0_event": "Aristotle, Politika -- comparative analysis of 158 constitutions, regime classification",
        "real_t0_source": "Miller F.D. (1995) Nature, Justice, and Rights in Aristotle's Politics, OUP, DOI:10.1093/0198237266.001.0001"
    },
    "Psychology": {
        "real_t0": -350,
        "real_t0_event": "Aristotle, De Anima -- first systematic treatise on mind, perception, memory, thought",
        "real_t0_source": "Nussbaum M.C. & Rorty A.O. (1992) Essays on Aristotle's De Anima, OUP, ISBN:978-0198236009"
    },
    "Sociology": {
        "real_t0": 1377,
        "real_t0_event": "Ibn Khaldun, Muqaddimah -- asabiyyah theory, empirical social analysis, rise/fall of civilizations",
        "real_t0_source": "Alatas S.F. (2006) International Sociology 21(6):782-795, DOI:10.1177/0268580906067790"
    },
}

def main():
    with open(ORIGINS_FILE, encoding="utf-8") as f:
        data = json.load(f)

    updated = 0
    for c in data["concepts"]:
        if c["name"] in L0_SOURCES and c["level"] == 0:
            src = L0_SOURCES[c["name"]]
            c["real_t0"] = src["real_t0"]
            c["real_t0_event"] = src["real_t0_event"]
            c["real_t0_source"] = src["real_t0_source"]
            updated += 1
            print(f'  {c["name"]:25s} -> t0={src["real_t0"]:>7d}')

    print(f"\nUpdated {updated}/19 Level 0 concepts")

    with open(ORIGINS_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
    print("Written to origins_to_source.json")

if __name__ == "__main__":
    main()
