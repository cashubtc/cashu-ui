import sys
from urllib.request import HTTPDefaultErrorHandler
from PyQt6 import QtWidgets, uic, QtGui, QtCore
from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import QWidget, QTableWidget
import asyncio
import os
import json
import time
from datetime import datetime
import base64
from itertools import groupby
from operator import itemgetter
from typing import List
from cashu.wallet import migrations
from cashu.wallet.crud import get_reserved_proofs, get_lightning_invoices
from cashu.core.helpers import fee_reserve, sum_proofs

from cashu.core.migrations import migrate_databases
from cashu.wallet.wallet import Wallet as Wallet
from cashu.core.settings import CASHU_DIR, DEBUG, ENV_FILE, LIGHTNING, MINT_URL, VERSION
from cashu.core.base import Proof, Invoice


import os

app = QtWidgets.QApplication(sys.argv)
app.setApplicationName("Cashu")

walletname = "wallet"
wallet = Wallet(MINT_URL, os.path.join(CASHU_DIR, walletname))


async def init_wallet(wallet: Wallet):
    """Performs migrations and loads proofs from db."""
    await migrate_databases(wallet.db, migrations)
    await wallet.load_mint()
    await wallet.load_proofs()


def table_headers(table: QTableWidget, headers: List[str]):
    table.setRowCount(table.rowCount() - 1)
    table.setColumnCount(len(headers))
    table.horizontalHeader().setDefaultAlignment(Qt.AlignmentFlag.AlignLeft)
    table.setHorizontalHeaderLabels(headers)
    table.resizeColumnsToContents()
    table.resizeRowsToContents()


def resource_path(relative_path):
    """Get absolute path to resource, works for dev and for PyInstaller"""
    try:
        # PyInstaller creates a temp folder and stores path in _MEIPASS
        base_path = sys._MEIPASS
    except Exception:
        base_path = os.path.abspath(".")

    return os.path.join(base_path, relative_path)


class App:
    def __init__(self):
        self.window = uic.loadUi(resource_path("ui/mainwindow.ui"))
        self.window.button_send.clicked.connect(self.button_send_clicked)
        self.window.button_receive.clicked.connect(self.button_receive_clicked)
        self.window.button_pay.clicked.connect(self.button_pay_clicked)
        self.window.button_invoice.clicked.connect(self.button_invoice_clicked)
        self.window.show()
        asyncio.run(init_wallet(wallet))
        self.set_app_icon()
        self.init_mainwindow()
        app.exec()
        return

    def set_app_icon(self):
        # set app icon
        app_icon = QtGui.QIcon()
        app_icon.addFile("ui/icons/16x16.png", QtCore.QSize(16, 16))
        app_icon.addFile("ui/icons/24x24.png", QtCore.QSize(24, 24))
        app_icon.addFile("ui/icons/32x32.png", QtCore.QSize(32, 32))
        app_icon.addFile("ui/icons/48x48.png", QtCore.QSize(48, 48))
        app_icon.addFile("ui/icons/256x256.png", QtCore.QSize(256, 256))
        app.setWindowIcon(app_icon)

    def init_mainwindow(self):
        self.window.tabWidget.setTabText(0, "Tokens")
        self.window.tabWidget.setTabText(1, "Pending")
        self.update_balance()
        self.window.label_mint_url.setText(f"Mint: {wallet.url}")

        self.list_amounts()
        self.list_pending()
        self.list_invoices()

    def update_balance(self):
        self.window.label_balance.setText(f"{wallet.available_balance} sat")

    def list_pending(self):
        table: QTableWidget = self.window.table_pending
        table.setRowCount(1)

        async def run(*args, **kwargs):
            reserved_proofs = await get_reserved_proofs(wallet.db)
            if len(reserved_proofs):
                print(f"--------------------------\n")
                sorted_proofs = sorted(reserved_proofs, key=itemgetter("send_id"))
                for i, (key, value) in enumerate(
                    groupby(sorted_proofs, key=itemgetter("send_id"))
                ):
                    grouped_proofs = list(value)
                    coin = await wallet.serialize_proofs(grouped_proofs)
                    coin_hidden_secret = await wallet.serialize_proofs(
                        grouped_proofs, hide_secrets=True
                    )
                    reserved_date = datetime.utcfromtimestamp(
                        int(grouped_proofs[0].time_reserved)
                    ).strftime("%Y-%m-%d %H:%M:%S")

                    print(
                        f"#{i} Amount: {sum_proofs(grouped_proofs)} sat Time: {reserved_date} ID: {key}\n"
                    )
                    print(f"With secret: {coin}\n\nSecretless: {coin_hidden_secret}\n")
                    print(f"--------------------------\n")

                    rowPosition = table.rowCount() - 1
                    table.insertRow(rowPosition)
                    table.setItem(
                        rowPosition,
                        0,
                        QtWidgets.QTableWidgetItem(str(sum_proofs(grouped_proofs))),
                    )
                    table.setItem(rowPosition, 1, QtWidgets.QTableWidgetItem(str(coin)))
                    table.setItem(
                        rowPosition,
                        2,
                        QtWidgets.QTableWidgetItem(str(reserved_date) or "none"),
                    )
                    table.setItem(rowPosition, 3, QtWidgets.QTableWidgetItem(str(key)))
            table_headers(table, ["amount", "token", "date", "id"])

        self.async_warpper(run)

    def list_amounts(self):

        table: QTableWidget = self.window.table_tokens
        table.setRowCount(1)
        sorted_proofs = sorted(wallet.proofs, key=lambda p: p.amount)
        for i, (key, value) in enumerate(groupby(sorted_proofs, lambda p: p.amount)):
            grouped_proofs = list(value)
            n_tokens = len(grouped_proofs)
            if n_tokens < 1:
                continue

            rowPosition = table.rowCount() - 1
            table.insertRow(rowPosition)
            table.setItem(rowPosition, 0, QtWidgets.QTableWidgetItem(str(key)))
            table.setItem(rowPosition, 1, QtWidgets.QTableWidgetItem(str(n_tokens)))
            table.setItem(
                rowPosition,
                2,
                QtWidgets.QTableWidgetItem(
                    str(sum([p.reserved or 0 for p in grouped_proofs]))
                )
                or "0",
            )
            table.setItem(
                rowPosition,
                3,
                QtWidgets.QTableWidgetItem(
                    str(" ".join(set([p.id for p in grouped_proofs])))
                ),
            )
        table_headers(table, ["amount", "count", "reserved", "keyset"])

    def list_invoices(self):
        table: QTableWidget = self.window.table_invoices
        table.setRowCount(1)

        async def run(*args, **kwargs):
            invoices: List[Invoice] = await get_lightning_invoices(db=wallet.db)
            for invoice in invoices:
                rowPosition = table.rowCount() - 1
                table.insertRow(rowPosition)
                table.setItem(
                    rowPosition, 0, QtWidgets.QTableWidgetItem(str(invoice.amount))
                )
                table.setItem(
                    rowPosition,
                    1,
                    QtWidgets.QTableWidgetItem(
                        str(f"{'paid' if invoice.paid else 'pending'}")
                    ),
                )
                table.setItem(
                    rowPosition, 2, QtWidgets.QTableWidgetItem(str(invoice.pr))
                )
            table_headers(table, ["amount", "status", "invoice"])
            table.cellClicked.connect(self.invoice_pending_clicked)

        self.async_warpper(run)

    def button_send_clicked(self, *args, **kwargs):
        async def run(*args, **kwargs):
            input = self.window.text_field.toPlainText()
            try:
                amount = int(input)
            except:
                print("no numeric amount in input field.")
                return
            if not amount > 0:
                print("amount must be greater than 0.")
                return

            _, send_proofs = await wallet.split_to_send(
                wallet.proofs, amount, set_reserved=True
            )
            coin = await wallet.serialize_proofs(send_proofs)
            print(f"Send Clicked! {coin}")
            self.window.text_field.setPlainText(coin)

        self.async_warpper(run)
        self.init_mainwindow()

    def button_receive_clicked(self, *args, **kwargs):
        async def run(*args, **kwargs):
            input = self.window.text_field.toPlainText()
            if len(input) < 16:
                raise Exception("no proof provided.")
            coin = input
            proofs = [Proof(**p) for p in json.loads(base64.urlsafe_b64decode(coin))]
            _, _ = await wallet.redeem(proofs)
            print(f"Receive Clicked! {coin}")
            self.window.text_field.setPlainText("")

        self.async_warpper(run)
        self.init_mainwindow()

    def button_pay_clicked(self, *args, **kwargs):
        print("Pay Clicked!")

        async def run(*args, **kwargs):
            input = self.window.text_field.toPlainText()
            if len(input) < 16 or not input.startswith("lnbc"):
                raise Exception("invalid Lightning invoice.")
            invoice = input
            proofs = await wallet.split_to_pay(invoice)
            await wallet.pay_lightning(proofs, invoice)
            self.window.text_field.setPlainText("Invoice paid.")

        self.async_warpper(run)
        self.init_mainwindow()

    def button_invoice_clicked(self, *args, **kwargs):
        print("Invoice Clicked!")

        # async def invoice_checker(amount, invoice: Invoice):
        #     check_until = time.time() + 5 * 60  # check for five minutes
        #     print("")
        #     print(
        #         f"Checking invoice ...",
        #         end="",
        #         flush=True,
        #     )
        #     paid = False
        #     while time.time() < check_until and not paid:
        #         time.sleep(3)
        #         try:
        #             await wallet.mint(amount, invoice.hash)
        #             paid = True
        #             self.window.text_field.setPlainText("Invoice paid.")
        #         except Exception as e:
        #             self.show_error(str(e))

        async def run(*args, **kwargs):
            input = self.window.text_field.toPlainText()
            try:
                amount = int(input)
            except:
                print("no numeric amount in input field.")
                return
            if not amount > 0:
                print("amount must be greater than 0.")
                return
            invoice = await wallet.request_mint(amount)
            if invoice.pr:
                self.window.text_field.setPlainText(invoice.pr)
                return amount, invoice

        amount, invoice = self.async_warpper(run)

        # loop = asyncio.new_event_loop()
        # # asyncio.set_event_loop(loop)
        # # loop.create_task(invoice_checker(amount=amount, invoice=invoice))
        # # asyncio.ensure_future(invoice_checker(amount=amount, invoice=invoice))
        # # loop.run_forever()
        # loop.run_in_executor(
        #     None, invoice_checker, dict(amount=amount, invoice=invoice)
        # )

        self.init_mainwindow()

    def invoice_pending_clicked(self, *args, **kwargs):
        """Activates when the user presses the "pending" cell in the invoice table."""

        async def run(*args, **kwargs):
            print(f"clicked {args}")
            if args[1] == 1:
                # pending column clicked
                invoices: List[Invoice] = await get_lightning_invoices(db=wallet.db)
                # get correct invoice
                invoice = invoices[args[0]]
                try:
                    await wallet.mint(invoice.amount, invoice.hash)
                    paid = True
                    self.window.text_field.setPlainText("Invoice paid.")
                except Exception as e:
                    self.show_error(str(e))
                    pass

        self.async_warpper(run, *args, **kwargs)
        self.init_mainwindow()

    def async_warpper(self, f, *args, **kwargs):
        try:
            return asyncio.run(f(*args, **kwargs))
        except Exception as e:
            self.show_error(str(e))
            return e

    def show_error(self, msg):
        dlg = QtWidgets.QMessageBox.critical(
            self.window,
            "Error",
            f"Error: {msg}",
            buttons=QtWidgets.QMessageBox.StandardButton.Ok,
        )


if __name__ == "__main__":
    app = App()
