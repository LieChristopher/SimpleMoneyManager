import streamlit as st
from dotenv import load_dotenv
import os
import pandas as pd
import datetime
import models
import parse_pdf
import pymupdf
import json

load_dotenv()

PROJECT_PATH = os.environ.get("PROJECT_PATH")
os.chdir(PROJECT_PATH)
st.set_page_config(layout="wide")

if "to_import" not in st.session_state:
    st.session_state.to_import = models.TransactionDataframe()

def import_transactions(file, platform, password):
    transactionDf = models.TransactionDataframe()
    if platform == "CIMB Niaga Payroll":
        transactionDf = parse_pdf.parse_cimb(file,password)
    elif platform == "GoPay":
        transactionDf = parse_pdf.parse_gojek(file)
    elif platform == "BCA":
        transactionDf = parse_pdf.parse_bca(file)
    # elif platform == "OCTO Pay":
    #     transactionDf = parse_pdf.parse(file)
    st.session_state.to_import.concatDF(transactionDf)

def unselect_individual():
    st.session_state.individual_value = models.TransactionDataframe().none_selected()

# @st.cache_resource
def get_import(imported_file, platform, password):
    try:
        if imported_file is not None:
            doc = pymupdf.open(stream=imported_file.read(), filetype="pdf")
        import_transactions(doc, platform, password)
    except Exception as e:
        st.toast("Import failed")
        st.toast(e)

# @st.cache_resource
def get_history(imported_file):
    import_df = models.TransactionDataframe()
    if imported_file is not None:
        doc = pymupdf.open(stream=imported_file.read(), filetype="pdf")
        import_df = import_transactions(doc)
    return import_df

def add_to_compare():
    # st.session_state.selected_import
    return

def to_import_with_selections():
    # df_with_selections = pd.DataFrame()
    df_with_selections = st.session_state.to_import.getDF().copy()
    # return df_with_selections
    df_with_selections.insert(loc=0,column='Duplicate',value=False)
    return df_with_selections

def main():
    platform_list = json.loads(open("categories.json").read())["Transfer-Out"]

    col_import, col_history = st.columns([2,1])



    
    subcol_history = col_history.columns([1,3])
    subcol_history[0].text("History")
    with subcol_history[1].popover(
        "Import History",icon="📤"):
        history_file = st.file_uploader("History")
    # col_history.write("---")
    history_df = models.TransactionDataframe()
    if history_file is not None:
        history_df = models.TransactionDataframe(pd.read_excel(history_file))
    col_history.dataframe(history_df.getDF(),
                          on_select=add_to_compare,
                          selection_mode="multi-row",
                          key="selected_history",
                          )


    subcol_import = col_import.columns([1,2,1,2])
    subcol_import[0].text("Imported data")
    with subcol_import[1].popover(
        "Transaction data to Import",
        icon="📤"):
            platform = st.selectbox("Import Category",platform_list)
            password = st.text_input("Password (if needed)", type="password")
            imported_file = st.file_uploader("Import file")
            st.button("Import",
                      "importData",
                      on_click=get_import,
                      args=(imported_file, platform, password),
                      use_container_width=True,
                      )
    subcol_import[2].download_button(
        "Export",
        st.session_state.to_import.getDF().to_csv(),
        mime="text/csv",
        icon="📩",
        file_name="Money Manager Import.csv",
        use_container_width=True,
        )
    subcol_import[3].button(
        "Check for duplicates",
        use_container_width=True,
        )
    # col_import.write("---")
    
    # col_import.data_editor(st.session_state.to_import.getDF(),
    col_import.data_editor(to_import_with_selections(),
                         hide_index=True,
                         column_config={"Duplicate": st.column_config.CheckboxColumn(required=True)},
                         )
    pass


main()