import re
import sys
import pandas
import os
import argparse
from pathlib import Path

def save_data_to_csv(file: str, data: list[dict]):
    if len(data) > 0:
        columns = ",".join(data[0].keys())
        rows = "".join(
            [
                "\n" + ",".join([str(x).replace(",", ".") for x in d.values()])
                for d in data
            ]
        )

        ofd = open(file, "w", encoding="utf-8")
        ofd.write(columns + rows)
        ofd.close()
        print(f"successfully generated {file}")


def load_unemployment_xls(path: Path, countryName: str, outputDir: Path = None):
    unemployment_people_data: list[dict] = []
    unemployment_municipality_data: list[dict] = []
    unemployment_sector_data: list[dict] = []

    data_handlers = {
        1: (  # Total
            lambda data, province, municipality, date: unemployment_municipality_data.append(
                {
                    "Municipio": municipality,
                    "Provincia": province,
                    "Pais": countryName,
                    "Cantidad": data[1],
                    "Fecha": date,
                }
            )
        ),
        2: (  # H < 25
            lambda data, province, municipality, date: unemployment_people_data.append(
                {
                    "Municipio": municipality,
                    "Provincia": province,
                    "Pais": countryName,
                    "Rango de edad": "<25",
                    "Sexo": "Masculino",
                    "Cantidad": data[1],
                    "Fecha": date,
                }
            )
        ),
        3: (  # H 25-44
            lambda data, province, municipality, date: unemployment_people_data.append(
                {
                    "Municipio": municipality,
                    "Provincia": province,
                    "Pais": countryName,
                    "Rango de edad": "25-44",
                    "Sexo": "Masculino",
                    "Cantidad": data[1],
                    "Fecha": date,
                }
            )
        ),
        4: (  # H >=45
            lambda data, province, municipality, date: unemployment_people_data.append(
                {
                    "Municipio": municipality,
                    "Provincia": province,
                    "Pais": countryName,
                    "Rango de edad": ">=45",
                    "Sexo": "Masculino",
                    "Cantidad": data[1],
                    "Fecha": date,
                }
            )
        ),
        5: (  # M<25
            lambda data, province, municipality, date: unemployment_people_data.append(
                {
                    "Municipio": municipality,
                    "Provincia": province,
                    "Pais": countryName,
                    "Rango de edad": "<25",
                    "Sexo": "Femenino",
                    "Cantidad": data[1],
                    "Fecha": date,
                }
            )
        ),
        6: (  # M 25-44
            lambda data, province, municipality, date: unemployment_people_data.append(
                {
                    "Municipio": municipality,
                    "Provincia": province,
                    "Pais": countryName,
                    "Rango de edad": " 25-44",
                    "Sexo": "Femenino",
                    "Cantidad": data[1],
                    "Fecha": date,
                }
            )
        ),
        7: (  # M >=45
            lambda data, province, municipality, date: unemployment_people_data.append(
                {
                    "Municipio": municipality,
                    "Provincia": province,
                    "Pais": countryName,
                    "Rango de edad": ">=45",
                    "Sexo": "Femenino",
                    "Cantidad": data[1],
                    "Fecha": date,
                }
            )
        ),
        8: (  # Agricultura
            lambda data, province, municipality, date: unemployment_sector_data.append(
                {
                    "Municipio": municipality,
                    "Provincia": province,
                    "Pais": countryName,
                    "Sector": "Agricultura",
                    "Cantidad": data[1],
                    "Fecha": date,
                }
            )
        ),
        9: (  # Industria
            lambda data, province, municipality, date: unemployment_sector_data.append(
                {
                    "Municipio": municipality,
                    "Provincia": province,
                    "Pais": countryName,
                    "Sector": "Industria",
                    "Cantidad": data[1],
                    "Fecha": date,
                }
            )
        ),
        10: (  # Construcción
            lambda data, province, municipality, date: unemployment_sector_data.append(
                {
                    "Municipio": municipality,
                    "Provincia": province,
                    "Pais": countryName,
                    "Sector": "Construcción",
                    "Cantidad": data[1],
                    "Fecha": date,
                }
            )
        ),
        11: (  # Servicios
            lambda data, province, municipality, date: unemployment_sector_data.append(
                {
                    "Municipio": municipality,
                    "Provincia": province,
                    "Pais": countryName,
                    "Sector": "Servicios",
                    "Cantidad": data[1],
                    "Fecha": date,
                }
            )
        ),
        12: (  # Sin empleo anterior
            lambda data, province, municipality, date: unemployment_sector_data.append(
                {
                    "Municipio": municipality,
                    "Provincia": province,
                    "Pais": countryName,
                    "Sector": "Sin empleo anterior",
                    "Cantidad": data[1],
                    "Fecha": date,
                }
            )
        ),
    }

    excel = pandas.read_excel(path, "PARO", header=7, index_col=1)

    # filename info deconstruction
    filename = os.path.basename(path)
    filename_no_extension = filename.split(".")[0]
    filename_deconstructed = filename.split("_")

    province = filename_deconstructed[1]
    raw_date = filename_deconstructed[-1].split(".")[0]
    date = "{month}/{year}".format(month=raw_date[:2], year=raw_date[2:])

    # handlers for columns index to output-data
    for row in excel.iterrows():
        municipality = row[0]
        items = list(row[1].iteritems())

        # the first displayed column displays some kind of cell Id number. It's not useful.
        for columnIndex in range(1, len(items)):
            real_index = columnIndex - 1

            try:
                data_handlers[real_index](
                    items[real_index], province, municipality, date
                )
            except:
                # in case there's no defined data handler for the given column index
                pass

    output_dir = str(outputDir) + r"\\" if outputDir else ""
    save_data_to_csv(
        f"{output_dir}{filename_no_extension}_Unemploiment_People.csv",
        unemployment_people_data,
    )
    save_data_to_csv(
        f"{output_dir}{filename_no_extension}_Unemploiment_Municipality.csv",
        unemployment_municipality_data,
    )
    save_data_to_csv(
        f"{output_dir}{filename_no_extension}_Unemploiment_Sectors.csv",
        unemployment_sector_data,
    )


def load_contracts_xls(path: Path, countryName: str, outputDir: Path = None):
    contracts_people_data: list[dict] = []
    contracts_municipality_data: list[dict] = []
    contracts_sector_data: list[dict] = []

    data_handlers = {
        1: (  # Total
            lambda data, province, municipality, date: contracts_municipality_data.append(
                {
                    "Municipio": municipality,
                    "Provincia": province,
                    "Pais": countryName,
                    "Cantidad": data[1],
                    "Fecha": date,
                }
            )
        ),
        2: (  # H Inicio Indefinido
            lambda data, province, municipality, date: contracts_people_data.append(
                {
                    "Municipio": municipality,
                    "Provincia": province,
                    "Pais": countryName,
                    "Tipo de contrato": "Inicio Indefinido",
                    "Sexo": "Masculino",
                    "Cantidad": data[1],
                    "Fecha": date,
                }
            )
        ),
        3: (  # H Inicio Temporal
            lambda data, province, municipality, date: contracts_people_data.append(
                {
                    "Municipio": municipality,
                    "Provincia": province,
                    "Pais": countryName,
                    "Tipo de contrato": "Inicio Temporal",
                    "Sexo": "Masculino",
                    "Cantidad": data[1],
                    "Fecha": date,
                }
            )
        ),
        4: (  # H Convertido Indefinido
            lambda data, province, municipality, date: contracts_people_data.append(
                {
                    "Municipio": municipality,
                    "Provincia": province,
                    "Pais": countryName,
                    "Tipo de contrato": "Convertido Indefinido",
                    "Sexo": "Masculino",
                    "Cantidad": data[1],
                    "Fecha": date,
                }
            )
        ),
        5: (  # M Inicio Indefinido
            lambda data, province, municipality, date: contracts_people_data.append(
                {
                    "Municipio": municipality,
                    "Provincia": province,
                    "Pais": countryName,
                    "Tipo de contrato": "Inicio Indefinido",
                    "Sexo": "Femenino",
                    "Cantidad": data[1],
                    "Fecha": date,
                }
            )
        ),
        6: (  # M Inicio Temporal
            lambda data, province, municipality, date: contracts_people_data.append(
                {
                    "Municipio": municipality,
                    "Provincia": province,
                    "Pais": countryName,
                    "Tipo de contrato": "Inicio Temporal",
                    "Sexo": "Femenino",
                    "Cantidad": data[1],
                    "Fecha": date,
                }
            )
        ),
        7: (  # M Convertido Indefinido
            lambda data, province, municipality, date: contracts_people_data.append(
                {
                    "Municipio": municipality,
                    "Provincia": province,
                    "Pais": countryName,
                    "Tipo de contrato": "Convertido Indefinido",
                    "Sexo": "Femenino",
                    "Cantidad": data[1],
                    "Fecha": date,
                }
            )
        ),
        8: (  # Agricultura
            lambda data, province, municipality, date: contracts_sector_data.append(
                {
                    "Municipio": municipality,
                    "Provincia": province,
                    "Pais": countryName,
                    "Sector": "Agricultura",
                    "Cantidad": data[1],
                    "Fecha": date,
                }
            )
        ),
        9: (  # Industria
            lambda data, province, municipality, date: contracts_sector_data.append(
                {
                    "Municipio": municipality,
                    "Provincia": province,
                    "Pais": countryName,
                    "Sector": "Industria",
                    "Cantidad": data[1],
                    "Fecha": date,
                }
            )
        ),
        10: (  # Construcción
            lambda data, province, municipality, date: contracts_sector_data.append(
                {
                    "Municipio": municipality,
                    "Provincia": province,
                    "Pais": countryName,
                    "Sector": "Construcción",
                    "Cantidad": data[1],
                    "Fecha": date,
                }
            )
        ),
        11: (  # Servicios
            lambda data, province, municipality, date: contracts_sector_data.append(
                {
                    "Municipio": municipality,
                    "Provincia": province,
                    "Pais": countryName,
                    "Sector": "Servicios",
                    "Cantidad": data[1],
                    "Fecha": date,
                }
            )
        ),
    }

    excel = pandas.read_excel(path, "CONTRATOS", header=7, index_col=1)

    # filename info deconstruction
    filename = os.path.basename(path)
    filename_no_extension = filename.split(".")[0]
    filename_deconstructed = filename.split("_")

    province = filename_deconstructed[1]
    raw_date = filename_deconstructed[-1].split(".")[0]
    date = "{month}/{year}".format(month=raw_date[:2], year=raw_date[2:])

    # handlers for columns index to output-data
    for row in excel.iterrows():
        municipality = row[0]
        items = list(row[1].iteritems())

        # the first displayed column displays some kind of cell Id number. It's not useful.
        for columnIndex in range(1, len(items)):
            real_index = columnIndex - 1

            try:
                data_handlers[real_index](
                    items[real_index], province, municipality, date
                )
            except:
                # in case there's no defined data handler for the given column index
                pass

    output_dir = str(outputDir) + r"\\" if outputDir else ""
    save_data_to_csv(
        f"{output_dir}{filename_no_extension}_Contracts_People.csv",
        contracts_people_data,
    )
    save_data_to_csv(
        f"{output_dir}{filename_no_extension}_Contracts_Municipality.csv",
        contracts_municipality_data,
    )
    save_data_to_csv(
        f"{output_dir}{filename_no_extension}_Contracts_Sectors.csv",
        contracts_sector_data,
    )


def load_data(path: Path, countryName: str, outputDir: Path = None):
    load_unemployment_xls(path, countryName, outputDir)
    load_contracts_xls(path, countryName, outputDir)

def load_files_from_dir(path: Path, countryName: str, outputDir: Path = None):
    filename_re = re.compile("^MUNI_[A-Z]+_\d+.xls$")
    for file in path.iterdir():
        if (not file.is_file()):
            continue
        filename = os.path.basename(file)
        if (filename_re.match(filename) != None):
            load_data(file, countryName, outputDir)

# Usage Example
# path = Path(r"C:\Users\Ernesto\Downloads\Telegram Desktop", r"MUNI_ALICANTE_0721.xls")
# load_data(path, "España")

if (__name__ == "__main__"):
    arg_parser = argparse.ArgumentParser(
        prog="Onei Loader",
        description="Loader for onei unemploiment and contracts xls files",
    )

    path_group = arg_parser.add_mutually_exclusive_group(required = True)
    path_group.add_argument("-f","--file", help='xls file path')
    path_group.add_argument("-d","--directory", help='xls dir path')
    
    
    arg_parser.add_argument('-od', "--output-directory", nargs='?', help='Output directory')
    arg_parser.add_argument('country', help='Country to which the xls data belongs')

    # Execute parse_args()
    args = arg_parser.parse_args()
    args_dict = dict(args._get_kwargs())

    if (args_dict.get("directory") != None):
        load_files_from_dir(Path(args_dict.get("directory")), args_dict.get("country"), args_dict.get("output_directory"))
    else:
        load_data(args_dict.get("file"), args_dict.get("country"), args_dict.get("output_directory"))



