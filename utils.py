from xml.etree import ElementTree as ET
import bs4
import pandas as pd
import googlemaps
import os
import json

from dotenv import load_dotenv
load_dotenv()

gmaps = googlemaps.Client(key=os.environ["GOOGLE_GEOCODING_API_KEY"])

def html_table_to_df(html_path):
    """Reads html "Wahlergebnisse" table into pandas DataFrame.
    """
    
    with open(html_path, "r", encoding="utf-8") as html_f:
        html_content = html_f.read()

    soup = bs4.BeautifulSoup(html_content, features="lxml")
    rows = soup.find_all('tr')

    header_row = rows[0]
    columns = header_row.find_all("td")

    df_dict = dict()

    for i, c in enumerate(columns):
        content_column = list()
        for r in rows[1:-1]:
            cell = r.find_all("td")[i]
            if i >= 3:
                cell_text = "%d"%(int(cell.contents[0].contents[0]), )
            else:
                cell_text = cell.text
            content_column.append(cell_text)
        df_dict[c.text] = content_column

    df = pd.DataFrame.from_dict(df_dict)
    
    rename_dict = {"Wahlbe-rechtigte": "eligible_voters", "Wähler/innen": "voters", 'Throm, Alexander (CDU)': "CDU", 'Juratovic, Josip (SPD)': "SPD",
       'Fick, Thomas (GRÜNE)': "GRUENE", 'Link, Michael Georg (FDP)': "FDP",
       'Kögel, Jürgen (AfD)': "AFD", 'Wanner, Konrad (DIE LINKE)': "LINKE", 'Sonstige': "SONSTIGE"}

    df = df.rename(rename_dict, axis="columns")

    def extract_location(w):
        return w.split("(")[0].strip()

    def extract_id(w):
        return w.split("(")[1][:-1].strip()

    df["location_address"] = df["Wahlbezirk"].map(extract_location)
    df["location_id"] = df["Wahlbezirk"].map(extract_id)
    del df["Wahlbezirk"]

    return df


def get_gps_from_location(df, address_col="location_address", suffix="Heilbronn"):
    """Queries Google Geocoding API and returns GPS coordinates of PoIs.
    """

    resp_dict = dict()

    for idx, row in df.iterrows():
        address_str = "%s %s"%(row[address_col], suffix)

        # Geocoding an address
        geocode_result = gmaps.geocode(address_str)

        resp_dict[address_str] = geocode_result

        loc_result = geocode_result[0]["geometry"]["location"]
        lat_list.append(loc_result["lat"])
        lon_list.append(loc_result["lng"])

    json_str = json.dumps(resp_dict)
    with open("geocode-results.json", "w") as f:
        f.write(json_str)


def get_gps_from_google_json(df, address_col="location_address", suffix="Heilbronn", json_map="data/geocode-results.json"):
    
    with open(json_map, "r", encoding="utf-8") as f:
        map_dict = json.loads(f.read())

    lat_list = list()
    lon_list = list()
    for idx, row in df.iterrows():
        address_str = "%s %s"%(row[address_col], suffix)
        geocode_result = map_dict[address_str]

        loc_result = geocode_result[0]["geometry"]["location"]
        lat_list.append(loc_result["lat"])
        lon_list.append(loc_result["lng"])

    df["latitude"] = lat_list
    df["longitude"] = lon_list

    return df


if __name__ == "__main__":

    html_path = "./data/wahlen17.html"
    df = html_table_to_df(html_path)

    print(df.head(10))

    df = get_gps_from_google_json(df, json_map="data/geocode-results.json")

    print(df.head(10))

    df.to_csv("wahlen17_hn_geo.csv", sep=",", index=False)