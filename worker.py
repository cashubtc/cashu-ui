from PyQt6.QtCore import QObject, pyqtSignal, pyqtSlot
import time
from cashu.core.base import Invoice
import asyncio


class CheckInvoiceWorker(QObject):
    """
    Worker that periodically checks whether an invoice has been paid.
    """

    def __init__(self, mint, invoice: Invoice):
        super().__init__()
        self.invoice = invoice
        self.mint = mint

    finished = pyqtSignal()
    strReady = pyqtSignal(str)

    @pyqtSlot()
    def procCounter(self):  # A slot takes no params
        print(f"Checking invoice id {self.invoice.id}")
        for i in range(1, 60): # check for 5 minutes
            try:
                asyncio.run(self.mint(self.invoice.amount, id=self.invoice.id))
                self.strReady.emit("paid")
                break
            except Exception as e:
                self.strReady.emit(str(e))
                pass
            time.sleep(5)

        self.finished.emit()

    def stop(self):
        print("terminating thread")
        self.terminate()


class LoadMintWorker(QObject):
    """
    Worker that loads the mint in a separate thread. Necessary
    for example for starting Tor which takes a certain time.
    """

    def __init__(self, mint):
        super().__init__()
        self.mint = mint

    finished = pyqtSignal()

    @pyqtSlot()
    def procLoadMint(self):  # A slot takes no params
        asyncio.run(self.mint.load_mint())
        self.finished.emit()


class UpdateWalletStateWorker(QObject):
    """
    Worker that periodically sends a signal if the mint is loaded.
    """

    def __init__(self, wallet):
        super().__init__()
        self.wallet = wallet

    update = pyqtSignal()

    @pyqtSlot()
    def procCheckWalletState(self):  # A slot takes no params
        while True:
            time.sleep(3)
            # this is the check that the mint is loaded, very ugly
            # might break in the future
            if hasattr(self.wallet, "keys"):
                # if mint is loaded send out a regular update signal
                self.update.emit()
