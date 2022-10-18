from PyQt6.QtCore import QObject, pyqtSignal, pyqtSlot
import time
from cashu.core.base import Invoice
import asyncio


class Worker(QObject):
    def __init__(self, mint, invoice: Invoice):
        super().__init__()
        self.invoice = invoice
        self.mint = mint

    finished = pyqtSignal()
    intReady = pyqtSignal(int)
    strReady = pyqtSignal(str)

    @pyqtSlot()
    def procCounter(self):  # A slot takes no params
        print(f"Checking invoice hash {self.invoice.hash}")
        for i in range(1, 10):
            try:
                asyncio.run(self.mint(self.invoice.amount, self.invoice.hash))
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
