from datetime import datetime
import re
import pandas as pd
import pymupdf
import models

DATEFORMAT_BCA = r'\d{1,2}\/\d{1,2}\/\d{4}'
DATEFORMAT_CIMB = r'\d{2}\/\d{2}\n\d{2}\/\d{2}'
SPACEFORMAT_3 = r'[\s]{3,}'
SPACEFORMAT_4 = r'[\s]{4,}'
DATEFORMAT_MDY = '%m/%d/%Y %H:%M:%S'
DATEFORMAT_YMD = '%Y-%m-%d %H:%M:%S'
DATEFORMAT_DMYP = '%d/%m/%Y %I:%M:%S %p'

def change_dateformat(datetime_str:str, from_dateformat:str, to_dateformat:str):
    return datetime.strptime(datetime_str, from_dateformat).strftime(to_dateformat) 
def ymd_to_mdy(datetime_str:str):
    return datetime.strptime(datetime_str, DATEFORMAT_YMD).strftime(DATEFORMAT_MDY)
def mdy_to_ymd(datetime_str:str):
    return datetime.strptime(datetime_str, DATEFORMAT_MDY).strftime(DATEFORMAT_YMD)

def read_html(path:str):
    html_df = pd.read_html(path)
    html_df = pd.DataFrame(html_df[0])
    html_df.loc[[0], 10] = "Account.1"
    html_df.columns = html_df.loc[0]
    html_df.drop(index=0, inplace=True)
    html_df["Date"] = html_df["Date"].apply(mdy_to_ymd)
    return html_df
def read_tsv(path:str):
    tsv_df = pd.read_csv(path, delimiter="\t", index_col=0)
    return tsv_df
def html_to_tsv(path:str):
    html_df = read_html(path)
    newpath = path.split(".")[0]+".tsv"
    html_df.to_csv(newpath, sep="\t")
    return newpath

def read_cimb(doc: pymupdf.Document, password:str=""):
    # doc = pymupdf.open(doc_path)
    doc.authenticate(password)
    result = ""
    for page in doc:
        result = result + page.get_text()
    # year = doc[0].get_text().split("Tanggal Laporan\nStatement Date\n:\n")[1].split("\nTgl. Pembukaan\nOpening Date\n:\n")[0][-4:]
    year = doc[0].get_text().split("\nLaporan Transaksi\nAccount Statement\n")[1].split("\nTanggal Laporan\nStatement Date\n:\n")[0][-4:]
    # year = doc[0].get_text()
    result = result.split("SALDO AWAL")[1].split("\nTotal")[0].split("SALDO AKHIR")[0]
    result = re.split("("+DATEFORMAT_CIMB+")", result)[1:]
    return year, result

def parse_cimb(doc_path:str, password:str=""):
    year, result = read_cimb(doc_path, password)
    date_chunk = [str(datetime.strptime(res.split('\n')[0]+"/"+year,"%d/%m/%Y")) for res in result[0::2]]
    trans_chunk = models.TransactionDataframe()
    for item in zip(date_chunk, result[1::2]):

        info = item[1].split("\n")
        if info[-1] == "":
            info.pop()
        _dict = {}
        _dict["date"] = item[0],
        _dict["desc"] = info[1],
        _dict["value"] = float(info[-2].replace(",",""))
        # _dict["value"] = item[-2]
        _dict["platform_to"] = None
        _dict["platform_from"] = "CIMB Niaga Payroll"
        if info[1] == "OVERBOOKING": #Transfer
            trans_chunk.addTransferItem(
                datetime = _dict["date"],
                account_from = _dict["platform_from"],
                transfer_fee = 0,
                account_to = "OCTO Pay",
                value = _dict["value"],
                note = _dict["desc"])
        if info[1] == "TR TO REMITT": #Transfer
            trans_chunk.addTransferItem(
                datetime = _dict["date"],
                account_from = _dict["platform_from"],
                transfer_fee = 0,
                account_to = "BCA",
                value = _dict["value"],
                note = _dict["desc"])
        if info[1] == "DIRECT CREDIT": #Income
            trans_chunk.addIncomeItem(
                datetime = _dict["date"],
                account_from = _dict["platform_from"],
                value = _dict["value"],
                note = _dict["desc"],
                category = "Salary",
                )
        if info[1] == "CREDIT PROFIT/HIBAH": #Income
            trans_chunk.addIncomeItem(
                datetime = _dict["date"],
                account_from = _dict["platform_from"],
                value = _dict["value"],
                note = _dict["desc"],
                category = "Interest",
                )
        if info[1] == "WITHHOLDING TAX": #expense
            trans_chunk.addExpenseItem(
                datetime=_dict["date"],
                account_from = _dict["platform_from"],
                value = _dict["value"],
                note = _dict["desc"],
                category = "Other",
                )
    return trans_chunk

def read_bca(doc: pymupdf.Document):
    # doc = pymupdf.open(doc_path)
    result = []
    for page in doc: # iterate the document pages
        transaction_strings = re.split(pattern="("+DATEFORMAT_BCA+")",
            # re.split(pattern=SPACEFORMAT, string=text) for text in
                  string=
                  " ".join(
                      page.get_text().split("TANGGAL\nKETERANGAN\nMUTASI\n")[1]\
                        .split("Bersambung ke Halaman berikutnya")[0]\
                        .split('\n')
            ))[1:]
        transaction_strings = ["   ".join(item) for item in zip(transaction_strings[0::2], transaction_strings[1::2])]
        result.extend(transaction_strings)
    return result

def parse_bca(doc_path:str):
    transaction_strings = read_bca(doc_path)
    result = models.TransactionDataframe()
    for transaction_string in transaction_strings:
        # st.code(transaction_string)
        item = {
                "tag": "",
                "date": None,
                "desc": "",
                "value": "0",
                "platform": "BCA",
                "type": None,
            }
        original_transaction_string = transaction_string
        if "TRANSAKSI DEBIT" in transaction_string:
            item["tag"] = "TRANSAKSI DEBIT"
            transaction_string = transaction_string.split("TRANSAKSI DEBIT")
            transaction_string[0] = re.split(pattern=SPACEFORMAT_3, string=transaction_string[0])
            item["date"] = transaction_string[0][0]
            item["desc"] = transaction_string[0][3].split(".00")[1]
            item["value"] = transaction_string[1][:-4]
        elif "TRSF E-BANKING" in transaction_string:
            item["tag"] = "TRSF E-BANKING"
            transaction_string = transaction_string.split("TRSF E-BANKING")
            item["value"] = transaction_string[1][5:-4]
            
            transaction_string[0] = re.split(pattern=SPACEFORMAT_3, string=transaction_string[0])
            # st.write(transaction_string[0])
            item["date"] = transaction_string[0][0][0:10]
            if len(transaction_string[0][1])>18:
                item["desc"] = transaction_string[0][1].split("/")[-1]#[18:]
            else:
                item["desc"] = " ".join(transaction_string[0][2:]).split(".00")[1].strip()
                # item["desc"] = transaction_string[0][0]
        elif "FLAZZ BCA" in transaction_string:
            item["tag"] = "FLAZZ BCA"
            transaction_string = transaction_string.split("FLAZZ BCA")
            transaction_string[0] = re.split(pattern=SPACEFORMAT_3, string=transaction_string[0])
            item["date"] = transaction_string[0][0]
            item["desc"] = "TOPUP FLAZZ BCA"
            item["value"] = transaction_string[1][:-4]
        elif "KARTU DEBIT" in transaction_string:
            item["tag"] = "KARTU DEBIT"
            transaction_string = transaction_string.split("KARTU DEBIT")
            transaction_string[0] = re.split(pattern=SPACEFORMAT_3, string=transaction_string[0])
            # item["date"] = transaction_string[0][0][0:10]
            item["date"] = transaction_string[0][0][0:10]
            item["desc"] = transaction_string[0][1]
            item["value"] = transaction_string[1][6:-4]
        elif "BUNGA" in transaction_string:
            item["tag"] = "BUNGA"
            transaction_string = transaction_string.split(item["tag"])
            item["date"] = transaction_string[0][0:10]
            item["desc"] = item["tag"]
            item["value"] = transaction_string[1][2:-4]
        else:
            item["tag"] = "OTHER"
            item["desc"] = [transaction_string]
            item["value"] = "0"
            item["date"] = transaction_string[:10]
        # return transaction_string
        if "," in item["value"]:
            item["value"] = item["value"].replace(",","")
        item["value"] = float(item["value"])
        item["date"] = str(datetime.strptime(item["date"],"%d/%m/%Y"))
        
        if "DB" in original_transaction_string:
            if "GOPAY ONE" in item["desc"]:
                result.addTransferItem(
                    datetime = item["date"],
                    account_from = item["platform"],
                    account_to = "GoPay",
                    value = item["value"]-1000,
                    transfer_fee=1000,
                    note = item["tag"],
                    description = item["desc"]
                )
            else:
                result.addExpenseItem(
                    datetime = item["date"],
                    account_from = item["platform"],
                    value = item["value"],
                    note = item["tag"],
                    description = item["desc"]
                )
        else:
            result.addIncomeItem(
                datetime = item["date"],
                account_from = item["platform"],
                value = item["value"],
                note = item["tag"],
                description = item["desc"]
            )
    return result

def read_gojek(doc: pymupdf.Document):
    # doc = pymupdf.open(doc_path)
    i = 0
    result = pd.DataFrame()
    for page in doc:
        tables = pymupdf.find_tables(page)
        if i == 0:
            result = pd.DataFrame(tables[0].extract())
            i = 1
        else:
            result = pd.concat([result, pd.DataFrame(tables[0].extract())], ignore_index=True)
    result.columns = result.loc[0]
    result.drop(index=0, inplace=True)
    return result

def parse_gojek(doc_path:str):
    df = read_gojek(doc_path)
    df["Tanggal"] = df["Tanggal"].apply(change_dateformat, from_dateformat=DATEFORMAT_DMYP, to_dateformat=DATEFORMAT_YMD)
    df["Total dibayar"] = df["Total dibayar"].str.replace(".","").str.replace("Rp","").astype(float)
    df["Dari"] = df["Dari"].str.split('\n').str[0]
    df["Tujuan"] = df["Tujuan"].str.split('\n').str[0]
    # print(type(df["Dari"][1]))
    # df["Description"] = "To " + df["Tujuan"] + " From " + df["Dari"]
    df.replace({'\n':' '},regex=True,inplace=True)
    df["Description"] = "To " + df["Tujuan"]
    df.drop(columns=["No. transaksi"], inplace=True)
    df["Category"] = "Transport"
    df["Subcategory"] = None
    # return df.loc[df["Layanan"].isin(["GoRide", "GoCar", "GoCar Hemat", "GoTransit"]), "Category"]
    # df.loc[df["Layanan"].isin(["GoRide", "GoCar", "GoCar Hemat", "GoTransit"]), "Category"] = models.Categories.Expense.Transport
    df.loc[df["Layanan"].isin(["GoFood"]), "Category"] = "Food"
    
    df.loc[df["Layanan"].isin(["GoFood"]), "Subcategory"] = "EatingOut"
    df.loc[df["Layanan"].isin(["GoTransit"]), "Subcategory"] = "Train"
    df.loc[df["Layanan"].isin(["GoRide", "GoCar", "GoCar Hemat"]), "Subcategory"] = "Cab"
    df.rename(columns={"Tanggal":"Date",
                       "Metode\nbayar":"Account",
                       "Layanan":"Note",
                       "Total dibayar":"Amount",
                       }, inplace=True)
    df["IDR"] = df["Amount"]
    df["Account.1"] = df["Amount"]
    df["Currency"] = "IDR"
    df["Income/Expense"] = "Expense"
    return models.TransactionDataframe(df[['Date', 'Account', 'Category', 'Subcategory', 'Note', 'IDR', 'Income/Expense', 'Description', 'Amount', 'Currency', 'Account.1']])