from io import BytesIO

from rdkit import Chem
from rdkit.Chem import Crippen, Descriptors, Draw, Lipinski, rdMolDescriptors


def molecule_image(smiles: str) -> BytesIO | None:
    molecule = Chem.MolFromSmiles(smiles)
    if molecule is None:
        return None
    image = Draw.MolToImage(molecule, size=(640, 480), kekulize=True)
    output = BytesIO()
    image.save(output, format="PNG")
    output.seek(0)
    return output


def molecule_descriptors(smiles: str) -> dict[str, str]:
    """Calculate descriptors for the supplied, unmodified SMILES structure."""
    molecule = Chem.MolFromSmiles(smiles)
    if molecule is None:
        raise ValueError("RDKit could not parse this SMILES string.")
    return {
        "Molecular formula": rdMolDescriptors.CalcMolFormula(molecule),
        "Molecular weight (g/mol)": f"{Descriptors.MolWt(molecule):.2f}",
        "Calculated LogP": f"{Crippen.MolLogP(molecule):.2f}",
        "TPSA (Å²)": f"{rdMolDescriptors.CalcTPSA(molecule):.2f}",
        "H-bond donors": str(Lipinski.NumHDonors(molecule)),
        "H-bond acceptors": str(Lipinski.NumHAcceptors(molecule)),
        "Rotatable bonds": str(Lipinski.NumRotatableBonds(molecule)),
        "Ring count": str(rdMolDescriptors.CalcNumRings(molecule)),
        "SMILES": smiles,
    }
