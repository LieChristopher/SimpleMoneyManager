import pandas as pd
import datetime as dt
import json

from parse_pdf import DATEFORMAT_YMD

class CURRENCY:
    IDR = "IDR"

class TransactionDataframe:
    def __init__(self, df = None):
        self.__df = pd.DataFrame(columns=["Date", "Account", "Category", "Subcategory", "Note", "IDR", "Income/Expense", "Description", "Amount", "Currency", "Account.1"])
        if df is not None:
            self.__df = df
        categories = json.loads(open("categories.json").read())
        self.categories_transaction = categories.keys()
        self.categories_expense = categories["Expense"]
        self.categories_income = categories["Income"]
        self.platform_list = categories["Transfer-Out"]
        json.loads(open("categories.json").read())
    def getDF(self):
        return self.__df
    def concatDF(self, tdf: 'TransactionDataframe'):
        result = pd.concat([self.getDF(), tdf.getDF()], ignore_index = True)
        self.__df = result
    def none_selected(self):
        return TransactionDataframe(pd.DataFrame({
                "Date": dt.datetime.now().strftime(DATEFORMAT_YMD),
                "Account": "",
                "Category": "",
                "Subcategory": "",
                "Note": "",
                "IDR": "",
                "Income/Expense": "",
                "Description": "",
                "Amount": 0,
                "Currency": "",
                "Account.1": "",
            }, index=[0]))
    def append(self, other_df:pd.DataFrame):
        self.__df = pd.concat([self.__df, other_df], ignore_index=True)
        self.__df.sort_values(by=["Date"], ascending=False, inplace=True)
    def addTransaction(self, type:str="", datetime:dt.datetime=None, account_from:str="", value:float=0, category:str="", subcategory:str=None, description:str=None, note:str=None, currency:str=CURRENCY.IDR):
        if self.__df.shape[0] == 0:
            self.__df = pd.DataFrame({
                "Date": datetime,
                "Account": account_from,
                "Category": category,
                "Subcategory": subcategory,
                "Note": note,
                "IDR": value,
                "Income/Expense": type,
                "Description": description,
                "Amount": value,
                "Currency": currency,
                "Account.1": value,
            }, index=[0])
        else:
            self.__df = pd.concat([self.__df, pd.DataFrame({
                "Date": datetime,
                "Account": account_from,
                "Category": category,
                "Subcategory": subcategory,
                "Note": note,
                "IDR": value,
                "Income/Expense": type,
                "Description": description,
                "Amount": value,
                "Currency": currency,
                "Account.1": value,
            }, index=[0])], ignore_index=True)
        self.__df.sort_values(by=["Date"], ascending=False, inplace=True)
    def addExpenseItem(self, datetime:str, account_from:str, value:float, category:str=None, subcategory:str=None, description:str=None, note:str=None):
        self.addTransaction(type="Expense",
                            datetime=datetime,
                            account_from=account_from,
                            value=value,
                            category=category,
                            subcategory=subcategory,
                            description=description,
                            note=note)
    def addIncomeItem(self, datetime:str, account_from:str, value:float, category:str=None, subcategory:str=None, description:str=None, note:str=None):
        self.addTransaction(type="Income",
                            datetime=datetime,
                            account_from=account_from,
                            value=value,
                            category=category,
                            subcategory=subcategory,
                            description=description,
                            note=note)
    def addTransferItem(self, datetime:str, account_from:str, account_to:str, value:float, description:str=None, note:str=None, transfer_fee:float = None):
        self.addTransaction(type="Transfer-Out",
                            account_from=account_from,
                            datetime=datetime,
                            value=value,
                            category=account_to,
                            description=description,
                            note=note)
        if transfer_fee and transfer_fee != 0:
            self.addExpenseItem(datetime=datetime,
                                account_from=account_from,
                                value=transfer_fee,
                                category="Other",
                                description=None,
                                note="Fees")
    def editTransactionItem(self, index:int, type:str, datetime:str, account_from:str, value:float, category:str=None, subcategory:str=None, description:str=None, note:str=None, transfer_fee:float = None):
        isCurrentlyIncome = self.__df.loc[index, "Income/Expense"] == "Income"
        isCurrentlyExpense = self.__df.loc[index, "Income/Expense"] == "Expense"
        isCurrentlyIncomeExpense = isCurrentlyExpense | isCurrentlyIncome
        isCurrentlyTransfer = self.__df.loc[index, "Income/Expense"] == "Transfer-Out"

        toBeIncome = type == "Income"
        toBeExpense = type == "Expense"
        toBeIncomeExpense = toBeExpense | toBeIncome
        toBeTransfer = type == "Transfer-Out"

        original_date = self.__df.loc[index, "Date"]
        transfer_fee_item = self.__df[self.__df["Note"] == "Fees" and
                                    self.__df["Date"] == original_date and
                                    self.__df["Income/Expense"] == "Expense"]
        
        self.__df.loc[index, "Date"] = datetime
        self.__df.loc[index, "Account"] = account_from
        self.__df.loc[index, "Category"] = category
        self.__df.loc[index, "Subcategory"] = subcategory
        self.__df.loc[index, "Note"] = note
        self.__df.loc[index, "IDR"] = value
        self.__df.loc[index, "Income/Expense"] = type
        self.__df.loc[index, "Description"] = description
        self.__df.loc[index, "Amount"] = value
        self.__df.loc[index, "Currency"] = CURRENCY.IDR
        self.__df.loc[index, "Account.1"] = value
        # if isCurrentlyIncomeExpense & toBeIncomeExpense:
            
        # if isCurrentlyIncomeExpense & toBeTransfer:
        # if isCurrentlyTransfer & toBeIncomeExpense:
        # if isCurrentlyTransfer & toBeTransfer:
            


        # self.addTransaction(type=CATEGORIES.Transfer,
        #                     account_from=account_from,
        #                     datetime=datetime,
        #                     value=value,
        #                     category=account_to,
        #                     description=description,
        #                     note=note)
        # if transfer_fee and transfer_fee != 0:
        #     self.addExpenseItem(datetime=datetime,
        #                         account_from=account_from,
        #                         value=transfer_fee,
        #                         category=CATEGORIES.TRANSFER.Category_List.Other,
        #                         description=None,
        #                         note="Fees")
