"""Choti dukaan ka stock aur rozmarra hisaab kitab."""

from datetime import datetime
from decimal import Decimal, InvalidOperation, ROUND_HALF_UP
from pathlib import Path
import sqlite3


# Database isi Python file ke paas banti hai, is liye record program band
# karne ke baad bhi mehfooz rehta hai.
DATABASE_FILE = Path(__file__).with_name("shop_accounting.db")
MONEY_PLACES = Decimal("0.01")
QUANTITY_PLACES = Decimal("0.001")
MONEY_SCALE = 100
QUANTITY_SCALE = 1000


def connect_database(database_file=DATABASE_FILE):
    """SQLite database khol kar zaroori tables tayyar kare."""
    connection = sqlite3.connect(database_file)
    connection.row_factory = sqlite3.Row
    connection.execute("PRAGMA foreign_keys = ON")
    connection.executescript(
        """
        CREATE TABLE IF NOT EXISTS products (
            id INTEGER PRIMARY KEY,
            name TEXT NOT NULL COLLATE NOCASE UNIQUE,
            unit TEXT NOT NULL,
            stock_milli INTEGER NOT NULL DEFAULT 0 CHECK (stock_milli >= 0),
            buy_price_paisa INTEGER NOT NULL CHECK (buy_price_paisa >= 0),
            sell_price_paisa INTEGER NOT NULL CHECK (sell_price_paisa >= 0),
            min_stock_milli INTEGER NOT NULL DEFAULT 0 CHECK (min_stock_milli >= 0)
        );

        CREATE TABLE IF NOT EXISTS contacts (
            id INTEGER PRIMARY KEY,
            name TEXT NOT NULL COLLATE NOCASE,
            phone TEXT NOT NULL DEFAULT '',
            kind TEXT NOT NULL CHECK (kind IN ('customer', 'supplier', 'both'))
        );

        CREATE TABLE IF NOT EXISTS invoices (
            id INTEGER PRIMARY KEY,
            kind TEXT NOT NULL CHECK (kind IN ('sale', 'purchase')),
            contact_id INTEGER REFERENCES contacts(id),
            created_at TEXT NOT NULL,
            total_paisa INTEGER NOT NULL CHECK (total_paisa >= 0),
            paid_paisa INTEGER NOT NULL DEFAULT 0
                CHECK (paid_paisa >= 0 AND paid_paisa <= total_paisa),
            note TEXT NOT NULL DEFAULT ''
        );

        CREATE TABLE IF NOT EXISTS invoice_lines (
            id INTEGER PRIMARY KEY,
            invoice_id INTEGER NOT NULL REFERENCES invoices(id),
            product_id INTEGER NOT NULL REFERENCES products(id),
            quantity_milli INTEGER NOT NULL CHECK (quantity_milli > 0),
            unit_price_paisa INTEGER NOT NULL CHECK (unit_price_paisa >= 0),
            line_total_paisa INTEGER NOT NULL CHECK (line_total_paisa >= 0),
            unit_cost_paisa INTEGER NOT NULL CHECK (unit_cost_paisa >= 0)
        );

        CREATE TABLE IF NOT EXISTS invoice_payments (
            id INTEGER PRIMARY KEY,
            invoice_id INTEGER NOT NULL REFERENCES invoices(id),
            paid_at TEXT NOT NULL,
            amount_paisa INTEGER NOT NULL CHECK (amount_paisa > 0),
            note TEXT NOT NULL DEFAULT ''
        );

        CREATE TABLE IF NOT EXISTS expenses (
            id INTEGER PRIMARY KEY,
            spent_at TEXT NOT NULL,
            category TEXT NOT NULL,
            amount_paisa INTEGER NOT NULL CHECK (amount_paisa > 0),
            note TEXT NOT NULL DEFAULT ''
        );

        CREATE INDEX IF NOT EXISTS invoices_kind_date
            ON invoices(kind, created_at);
        CREATE INDEX IF NOT EXISTS invoice_payments_invoice
            ON invoice_payments(invoice_id);
        """
    )
    return connection


def format_money(paisa):
    """Paison ko rupay ki do decimal places ke saath dikhaye."""
    rupees = Decimal(paisa) / MONEY_SCALE
    return f"Rs. {rupees:,.2f}"


def format_quantity(quantity_milli):
    """Quantity ko teen decimal places tak dikhaye."""
    return f"{quantity_milli / QUANTITY_SCALE:,.3f}"


def parse_money(text):
    """Rupay ko integer paison mein tabdeel kare; float rounding se bache."""
    amount = Decimal(text.strip()).quantize(MONEY_PLACES, rounding=ROUND_HALF_UP)
    if amount < 0:
        raise ValueError("Raqam zero ya us se zyada honi chahiye.")
    return int(amount * MONEY_SCALE)


def parse_quantity(text):
    """Quantity ko 0.001 unit ke integer hisse mein tabdeel kare."""
    quantity = Decimal(text.strip()).quantize(
        QUANTITY_PLACES, rounding=ROUND_HALF_UP
    )
    if quantity <= 0:
        raise ValueError("Quantity zero se zyada honi chahiye.")
    return int(quantity * QUANTITY_SCALE)


def ask_money(prompt, minimum=0, maximum=None):
    """Sahi money value dobara mangta rahe jab tak input durust na ho."""
    while True:
        try:
            amount = parse_money(input(prompt))
            if amount < minimum:
                print(f"Kam az kam {format_money(minimum)} likhein.")
            elif maximum is not None and amount > maximum:
                print(f"Zyada se zyada {format_money(maximum)} likhein.")
            else:
                return amount
        except (InvalidOperation, ValueError):
            print("Durust raqam likhein, misal: 1250 ya 1250.50.")


def ask_quantity(prompt):
    """Sahi quantity dobara mangta rahe jab tak input durust na ho."""
    while True:
        try:
            return parse_quantity(input(prompt))
        except (InvalidOperation, ValueError):
            print("Durust quantity likhein, misal: 2 ya 1.250.")


def ask_yes_no(prompt, default=True):
    """Yes/no sawal; khaali jawab default ko chunta hai."""
    hint = "Y/n" if default else "y/N"
    while True:
        answer = input(f"{prompt} [{hint}]: ").strip().lower()
        if not answer:
            return default
        if answer in ("y", "yes", "haan", "han"):
            return True
        if answer in ("n", "no", "nahin", "nahi"):
            return False
        print("Jawab y ya n mein dein.")


def list_products(connection):
    """Maujooda products ki mukhtasar fehrist dikhaye."""
    products = connection.execute(
        "SELECT * FROM products ORDER BY name"
    ).fetchall()
    if not products:
        print("Abhi koi item nahin. Pehle menu se item add karein.")
        return []
    print("\nID | Item | Stock | Unit | Khareed | Sale")
    print("-" * 68)
    for product in products:
        print(
            f"{product['id']} | {product['name']} | "
            f"{format_quantity(product['stock_milli'])} | {product['unit']} | "
            f"{format_money(product['buy_price_paisa'])} | "
            f"{format_money(product['sell_price_paisa'])}"
        )
    return products


def add_or_update_product(connection):
    """Naya item banaye ya purane item ka naam/rate update kare."""
    products = connection.execute(
        "SELECT * FROM products ORDER BY name"
    ).fetchall()
    if products:
        list_products(connection)
        chosen_id = input(
            "\nPurana item update karne ke liye us ka ID, "
            "naye item ke liye khaali Enter: "
        ).strip()
    else:
        chosen_id = ""

    if chosen_id:
        product = connection.execute(
            "SELECT * FROM products WHERE id = ?", (chosen_id,)
        ).fetchone()
        if product is None:
            print("Is ID ka item nahin mila.")
            return
        name = input(f"Item ka naam [{product['name']}]: ").strip()
        unit = input(f"Unit, misal piece/kg [{product['unit']}]: ").strip()
        # Khaali jawab par purana rate rakhna asaan rahe, is liye rate
        # input ko alag helper se parhte hain.
        buy_price = ask_optional_money(
            f"Khareed rate Rs. [{format_money(product['buy_price_paisa'])}]: ",
            product["buy_price_paisa"],
        )
        sell_price = ask_optional_money(
            f"Sale rate Rs. [{format_money(product['sell_price_paisa'])}]: ",
            product["sell_price_paisa"],
        )
        min_stock = ask_optional_quantity(
            f"Low-stock had [{format_quantity(product['min_stock_milli'])}]: ",
            product["min_stock_milli"],
        )
        with connection:
            connection.execute(
                """
                UPDATE products
                SET name = ?, unit = ?, buy_price_paisa = ?,
                    sell_price_paisa = ?, min_stock_milli = ?
                WHERE id = ?
                """,
                (
                    name or product["name"],
                    unit or product["unit"],
                    buy_price,
                    sell_price,
                    min_stock,
                    product["id"],
                ),
            )
        print("Item ki maloomat update ho gayi.")
        return

    name = input("Item ka naam: ").strip()
    unit = input("Unit (piece, kg, liter waghera): ").strip()
    if not name or not unit:
        print("Item ka naam aur unit khaali nahin ho sakte.")
        return
    buy_price = ask_money("Har unit ka khareed rate Rs.: ")
    sell_price = ask_money("Har unit ka sale rate Rs.: ")
    min_stock = ask_optional_quantity("Low-stock warning had (default 0): ", 0)
    try:
        with connection:
            connection.execute(
                """
                INSERT INTO products
                    (name, unit, buy_price_paisa, sell_price_paisa,
                     min_stock_milli)
                VALUES (?, ?, ?, ?, ?)
                """,
                (name, unit, buy_price, sell_price, min_stock),
            )
        print("Naya item save ho gaya. Stock purchase entry se add hoga.")
    except sqlite3.IntegrityError as error:
        if "products.name" in str(error):
            print("Is naam ka item pehle se maujood hai.")
        else:
            raise


def ask_optional_money(prompt, default):
    """Khaali input par purani/default money value wapas kare."""
    while True:
        text = input(prompt).strip()
        if not text:
            return default
        try:
            return parse_money(text)
        except (InvalidOperation, ValueError):
            print("Durust raqam likhein, misal: 1250 ya 1250.50.")


def ask_optional_quantity(prompt, default):
    """Khaali input par purani/default quantity value wapas kare."""
    while True:
        text = input(prompt).strip()
        if not text:
            return default
        try:
            quantity = Decimal(text).quantize(
                QUANTITY_PLACES, rounding=ROUND_HALF_UP
            )
            if quantity < 0:
                raise ValueError("Quantity manfi nahin ho sakti.")
            return int(quantity * QUANTITY_SCALE)
        except (InvalidOperation, ValueError):
            print("Zero ya us se zyada durust quantity likhein.")


def add_contact(connection):
    """Customer, supplier ya dono qisam ka karobari contact save kare."""
    name = input("Naam: ").strip()
    if not name:
        print("Naam khaali nahin ho sakta.")
        return
    phone = input("Phone number (optional): ").strip()
    print("Qisam: 1) Customer  2) Supplier  3) Dono")
    kind = {"1": "customer", "2": "supplier", "3": "both"}.get(
        input("Chunein: ").strip()
    )
    if kind is None:
        print("Ghalat selection.")
        return
    with connection:
        connection.execute(
            "INSERT INTO contacts (name, phone, kind) VALUES (?, ?, ?)",
            (name, phone, kind),
        )
    print("Contact save ho gaya.")


def choose_contact(connection, allowed_kinds, optional=False):
    """Invoice ke liye supplier/customer chunne dein."""
    placeholders = ", ".join("?" for _ in allowed_kinds)
    contacts = connection.execute(
        f"""
        SELECT * FROM contacts
        WHERE kind IN ({placeholders}) OR kind = 'both'
        ORDER BY name
        """,
        tuple(allowed_kinds),
    ).fetchall()
    if not contacts:
        if optional:
            print("Koi contact nahin; invoice ko kisi naam ke baghair save karein.")
            return None
        print("Is invoice ke liye pehle customer/supplier add karein.")
        return None
    print("\nContacts:")
    for contact in contacts:
        phone = f" ({contact['phone']})" if contact["phone"] else ""
        print(f"{contact['id']}) {contact['name']}{phone}")
    if optional:
        print("Khaali Enter = walk-in / ghair muayyan contact")
    while True:
        answer = input("Contact ID: ").strip()
        if optional and not answer:
            return None
        try:
            contact_id = int(answer)
        except ValueError:
            print("Durust ID likhein.")
            continue
        if any(contact["id"] == contact_id for contact in contacts):
            return contact_id
        print("Fehrist mein se ID chunein.")


def choose_product(products):
    """Dikhai gayi fehrist se product chunne dein."""
    while True:
        try:
            product_id = int(input("Item ID: ").strip())
        except ValueError:
            print("Durust ID likhein.")
            continue
        for product in products:
            if product["id"] == product_id:
                return product
        print("Fehrist mein se item ID chunein.")


def record_invoice(connection, kind):
    """Purchase/sale bill, us ke items, stock aur ibtidai payment save kare."""
    products = connection.execute(
        "SELECT * FROM products ORDER BY name"
    ).fetchall()
    if not products:
        print("Pehle kam az kam ek item add karein.")
        return
    list_products(connection)

    contact_id = choose_contact(
        connection,
        ("supplier",) if kind == "purchase" else ("customer",),
        optional=True,
    )
    lines = []
    total_paisa = 0
    while True:
        product = choose_product(products)
        quantity = ask_quantity(f"Quantity ({product['unit']}): ")
        if kind == "sale" and quantity > product["stock_milli"]:
            print(
                f"Stock kam hai. Maujooda stock: "
                f"{format_quantity(product['stock_milli'])} {product['unit']}"
            )
            if not ask_yes_no("Kya doosra item add karna hai?", default=False):
                return
            continue
        default_price = (
            product["buy_price_paisa"]
            if kind == "purchase"
            else product["sell_price_paisa"]
        )
        price = ask_optional_money(
            f"Har {product['unit']} ka rate Rs. "
            f"[{format_money(default_price)}]: ",
            default_price,
        )
        # Har line ko paison mein round karne se bill total hamesha
        # paison ki poori tadaad hota hai.
        line_total = int(
            (
                Decimal(quantity * price) / QUANTITY_SCALE
            ).quantize(Decimal("1"), rounding=ROUND_HALF_UP)
        )
        unit_cost = (
            price if kind == "purchase" else product["buy_price_paisa"]
        )
        lines.append(
            {
                "product_id": product["id"],
                "quantity_milli": quantity,
                "unit_price_paisa": price,
                "line_total_paisa": line_total,
                "unit_cost_paisa": unit_cost,
            }
        )
        total_paisa += line_total
        if not ask_yes_no("Kya ek aur item is bill mein add karna hai?"):
            break

    print(f"\nBill ka total: {format_money(total_paisa)}")
    paid_paisa = ask_money(
        "Abhi di/liye gaye paise Rs.: ",
        maximum=total_paisa,
    )
    if paid_paisa < total_paisa and contact_id is None:
        print(
            "Baqaya paise track karne ke liye customer/supplier select karna "
            "zaroori hai. Bill save nahin hua."
        )
        return
    note = input("Bill ka note (optional): ").strip()

    # Invoice, items, stock aur payment ek hi transaction mein save hote hain.
    # Darmiyan mein koi masla aaye to aadha bill database mein nahin rahega.
    with connection:
        cursor = connection.execute(
            """
            INSERT INTO invoices (kind, contact_id, created_at, total_paisa,
                                  paid_paisa, note)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (
                kind,
                contact_id,
                datetime.now().isoformat(timespec="seconds"),
                total_paisa,
                paid_paisa,
                note,
            ),
        )
        invoice_id = cursor.lastrowid
        for line in lines:
            connection.execute(
                """
                INSERT INTO invoice_lines
                    (invoice_id, product_id, quantity_milli,
                     unit_price_paisa, line_total_paisa, unit_cost_paisa)
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (
                    invoice_id,
                    line["product_id"],
                    line["quantity_milli"],
                    line["unit_price_paisa"],
                    line["line_total_paisa"],
                    line["unit_cost_paisa"],
                ),
            )
            if kind == "purchase":
                current_product = connection.execute(
                    "SELECT stock_milli, buy_price_paisa FROM products WHERE id = ?",
                    (line["product_id"],),
                ).fetchone()
                new_stock = (
                    current_product["stock_milli"] + line["quantity_milli"]
                )
                # Naye stock ke saath purane stock ki lagat mila kar
                # average cost rakhein; sale ka munafa isi se andaza hoga.
                average_cost = int(
                    (
                        Decimal(
                            current_product["stock_milli"]
                            * current_product["buy_price_paisa"]
                            + line["quantity_milli"]
                            * line["unit_price_paisa"]
                        )
                        / new_stock
                    ).quantize(Decimal("1"), rounding=ROUND_HALF_UP)
                )
                connection.execute(
                    """
                    UPDATE products
                    SET stock_milli = stock_milli + ?, buy_price_paisa = ?
                    WHERE id = ?
                    """,
                    (
                        line["quantity_milli"],
                        average_cost,
                        line["product_id"],
                    ),
                )
            else:
                update = connection.execute(
                    """
                    UPDATE products SET stock_milli = stock_milli - ?
                    WHERE id = ? AND stock_milli >= ?
                    """,
                    (
                        line["quantity_milli"],
                        line["product_id"],
                        line["quantity_milli"],
                    ),
                )
                if update.rowcount != 1:
                    raise ValueError("Stock badal gaya hai; sale dobara karein.")
        if paid_paisa:
            connection.execute(
                """
                INSERT INTO invoice_payments
                    (invoice_id, paid_at, amount_paisa, note)
                VALUES (?, ?, ?, ?)
                """,
                (
                    invoice_id,
                    datetime.now().isoformat(timespec="seconds"),
                    paid_paisa,
                    "Bill banate waqt di gayi raqam",
                ),
            )
    invoice_type = "Sale" if kind == "sale" else "Purchase"
    print(
        f"{invoice_type} bill #{invoice_id} save ho gaya. "
        f"Baqaya: {format_money(total_paisa - paid_paisa)}"
    )


def list_open_invoices(connection, kind):
    """Customer se leni ya supplier ko deni baqi invoices dikhaye."""
    open_invoices = connection.execute(
        """
        SELECT i.id, i.created_at, i.total_paisa, i.paid_paisa,
               c.name AS contact_name
        FROM invoices AS i
        LEFT JOIN contacts AS c ON c.id = i.contact_id
        WHERE i.kind = ? AND i.paid_paisa < i.total_paisa
        ORDER BY i.created_at, i.id
        """,
        (kind,),
    ).fetchall()
    if not open_invoices:
        print("Koi baqaya bill nahin.")
        return []
    print("\nBill ID | Tareekh | Naam | Total | Jama | Baqaya")
    print("-" * 90)
    for invoice in open_invoices:
        print(
            f"#{invoice['id']} | {invoice['created_at']} | "
            f"{invoice['contact_name'] or 'Naam nahin'} | "
            f"{format_money(invoice['total_paisa'])} | "
            f"{format_money(invoice['paid_paisa'])} | "
            f"{format_money(invoice['total_paisa'] - invoice['paid_paisa'])}"
        )
    return open_invoices


def record_invoice_payment(connection, kind):
    """Purane sale/purchase bill par mazeed payment jama kare."""
    invoices = list_open_invoices(connection, kind)
    if not invoices:
        return
    while True:
        try:
            invoice_id = int(input("\nBill ID: ").strip().lstrip("#"))
        except ValueError:
            print("Durust bill ID likhein.")
            continue
        invoice = next(
            (row for row in invoices if row["id"] == invoice_id), None
        )
        if invoice:
            break
        print("Baqaya bill ki fehrist mein se ID chunein.")
    remaining = invoice["total_paisa"] - invoice["paid_paisa"]
    amount = ask_money("Jama raqam Rs.: ", minimum=1, maximum=remaining)
    note = input("Payment ka note (optional): ").strip()
    with connection:
        connection.execute(
            """
            UPDATE invoices SET paid_paisa = paid_paisa + ? WHERE id = ?
            """,
            (amount, invoice_id),
        )
        connection.execute(
            """
            INSERT INTO invoice_payments
                (invoice_id, paid_at, amount_paisa, note)
            VALUES (?, ?, ?, ?)
            """,
            (
                invoice_id,
                datetime.now().isoformat(timespec="seconds"),
                amount,
                note,
            ),
        )
    print(f"Payment save ho gayi. Is bill ka naya baqaya: {format_money(remaining - amount)}")


def record_expense(connection):
    """Kiraya, bijli, tankhwa waghera ka kharcha register kare."""
    category = input("Kharchay ki qisam (misal: kiraya, bijli): ").strip()
    if not category:
        print("Kharchay ki qisam khaali nahin ho sakti.")
        return
    amount = ask_money("Kharchay ki raqam Rs.: ", minimum=1)
    note = input("Tafseel (optional): ").strip()
    with connection:
        connection.execute(
            """
            INSERT INTO expenses (spent_at, category, amount_paisa, note)
            VALUES (?, ?, ?, ?)
            """,
            (
                datetime.now().isoformat(timespec="seconds"),
                category,
                amount,
                note,
            ),
        )
    print("Kharcha save ho gaya.")


def show_stock_report(connection):
    """Stock aur low-stock warning ke saath inventory report de."""
    products = connection.execute(
        "SELECT * FROM products ORDER BY name"
    ).fetchall()
    if not products:
        print("Abhi koi item nahin.")
        return
    stock_value = 0
    print("\nItem | Maujooda stock | Unit | Khareed ke mutabiq qeemat | Alert")
    print("-" * 92)
    for product in products:
        value = int(
            (
                Decimal(product["stock_milli"] * product["buy_price_paisa"])
                / QUANTITY_SCALE
            ).quantize(Decimal("1"), rounding=ROUND_HALF_UP)
        )
        stock_value += value
        alert = (
            "LOW STOCK"
            if product["stock_milli"] <= product["min_stock_milli"]
            else ""
        )
        print(
            f"{product['name']} | {format_quantity(product['stock_milli'])} | "
            f"{product['unit']} | {format_money(value)} | {alert}"
        )
    print(f"\nKul stock ki andazati khareed qeemat: {format_money(stock_value)}")


def show_invoice_history(connection):
    """Recent sale aur purchase bills ki tafseel dikhaye."""
    invoices = connection.execute(
        """
        SELECT i.*, c.name AS contact_name
        FROM invoices AS i
        LEFT JOIN contacts AS c ON c.id = i.contact_id
        ORDER BY i.id DESC
        LIMIT 100
        """
    ).fetchall()
    if not invoices:
        print("Abhi koi bill nahin.")
        return
    print("\nAakhri 100 bills:")
    for invoice in invoices:
        label = "SALE" if invoice["kind"] == "sale" else "PURCHASE"
        balance = invoice["total_paisa"] - invoice["paid_paisa"]
        print(
            f"#{invoice['id']} {label} | {invoice['created_at']} | "
            f"{invoice['contact_name'] or 'Naam nahin'} | "
            f"Total {format_money(invoice['total_paisa'])} | "
            f"Jama {format_money(invoice['paid_paisa'])} | "
            f"Baqaya {format_money(balance)}"
        )
        lines = connection.execute(
            """
            SELECT p.name, il.quantity_milli, p.unit, il.line_total_paisa
            FROM invoice_lines AS il
            JOIN products AS p ON p.id = il.product_id
            WHERE il.invoice_id = ?
            """,
            (invoice["id"],),
        ).fetchall()
        for line in lines:
            print(
                f"   - {line['name']}: {format_quantity(line['quantity_milli'])} "
                f"{line['unit']} = {format_money(line['line_total_paisa'])}"
            )


def show_payment_history(connection):
    """Supplier ko ki aur customer se mili payments ka record dikhaye."""
    payments = connection.execute(
        """
        SELECT ip.paid_at, ip.amount_paisa, ip.note, i.id AS invoice_id,
               i.kind, c.name AS contact_name
        FROM invoice_payments AS ip
        JOIN invoices AS i ON i.id = ip.invoice_id
        LEFT JOIN contacts AS c ON c.id = i.contact_id
        ORDER BY ip.id DESC
        LIMIT 100
        """
    ).fetchall()
    if not payments:
        print("Abhi koi payment record nahin.")
        return
    print("\nAakhri 100 payments:")
    for payment in payments:
        direction = (
            "Customer se wasool"
            if payment["kind"] == "sale"
            else "Supplier ko ada"
        )
        print(
            f"{payment['paid_at']} | {direction} | "
            f"{payment['contact_name'] or 'Naam nahin'} | "
            f"Bill #{payment['invoice_id']} | "
            f"{format_money(payment['amount_paisa'])} | {payment['note']}"
        )


def show_expense_history(connection):
    """Darj kiye gaye kharchon ki tareekh aur tafseel dikhaye."""
    expenses = connection.execute(
        """
        SELECT spent_at, category, amount_paisa, note
        FROM expenses
        ORDER BY id DESC
        LIMIT 100
        """
    ).fetchall()
    if not expenses:
        print("Abhi koi kharcha record nahin.")
        return
    print("\nAakhri 100 kharchay:")
    for expense in expenses:
        print(
            f"{expense['spent_at']} | {expense['category']} | "
            f"{format_money(expense['amount_paisa'])} | {expense['note']}"
        )


def show_financial_summary(connection):
    """Kul sale, purchase, expenses, estimated profit aur baqaya dikhaye."""
    totals = connection.execute(
        """
        SELECT
            COALESCE(SUM(CASE WHEN kind = 'sale' THEN total_paisa ELSE 0 END), 0)
                AS sales,
            COALESCE(SUM(CASE WHEN kind = 'purchase' THEN total_paisa ELSE 0 END), 0)
                AS purchases,
            COALESCE(SUM(CASE WHEN kind = 'sale'
                              THEN paid_paisa ELSE 0 END), 0)
                AS sales_received,
            COALESCE(SUM(CASE WHEN kind = 'purchase'
                              THEN paid_paisa ELSE 0 END), 0)
                AS purchases_paid,
            COALESCE(SUM(CASE WHEN kind = 'sale'
                              THEN total_paisa - paid_paisa ELSE 0 END), 0)
                AS receivable,
            COALESCE(SUM(CASE WHEN kind = 'purchase'
                              THEN total_paisa - paid_paisa ELSE 0 END), 0)
                AS payable
        FROM invoices
        """
    ).fetchone()
    expenses = connection.execute(
        "SELECT COALESCE(SUM(amount_paisa), 0) FROM expenses"
    ).fetchone()[0]
    sale_lines = connection.execute(
        """
        SELECT line_total_paisa, quantity_milli, unit_cost_paisa
        FROM invoice_lines
        JOIN invoices ON invoices.id = invoice_lines.invoice_id
        WHERE invoices.kind = 'sale'
        """
    ).fetchall()
    # Har item ki lagat ko paison mein round kar ke total profit nikalein.
    profit = 0
    for line in sale_lines:
        line_cost = int(
            (
         Decimal(line["quantity_milli"] * line["unit_cost_paisa"])
         / QUANTITY_SCALE
            ).quantize(Decimal("1"), rounding=ROUND_HALF_UP)
        )
        profit += line["line_total_paisa"] - line_cost
    print("\n--- Kul hisaab (ab tak) ---")
    print(f"Kul sale:                  {format_money(totals['sales'])}")
    print(f"Kul purchase:              {format_money(totals['purchases'])}")
    print(f"Customer se wasool:        {format_money(totals['sales_received'])}")
    print(f"Supplier ko ada:           {format_money(totals['purchases_paid'])}")
    print(f"Customer se lena baqi:     {format_money(totals['receivable'])}")
    print(f"Supplier ko dena baqi:     {format_money(totals['payable'])}")
    print(f"Kul expenses:              {format_money(expenses)}")
    print(f"Andazati gross profit:     {format_money(profit)}")
    print(
        "Andazati net profit::       "
        f"{format_money(profit - expenses)}"
    )
    print(
        "Note: profit khareed ke waqt darj rate se andaza hai; "
        "yeh tax/accountant report ka badal nahin."
    )


def show_menu():
    """Roman Urdu main menu."""
    print(
        """
================ SHOP KA HISSAAB ================
1. Item add/update karein
2. Customer/supplier add karein
3. Nayi purchase / supplier bill aur stock add
4. Nayi sale / customer bill
5. Customer se baqi paise wasool karein
6. Supplier ko baqi paise ada karein
7. Kharcha darj karein
8. Stock aur low-stock report
9. Customer se leni raqam ki fehrist
10. Supplier ko deni raqam ki fehrist
11. Sale/purchase bills ki history
12. Kul hisaab aur munafa report
13. Wasooli/adaigi payment history
14. Kharchon ki history
0. Band karein
=====================================================
"""
    )


def main():
    """Program ka menu chala kar shop ka database khula rakhe."""
    connection = connect_database()
    actions = {
        "1": lambda: add_or_update_product(connection),
        "2": lambda: add_contact(connection),
        "3": lambda: record_invoice(connection, "purchase"),
        "4": lambda: record_invoice(connection, "sale"),
        "5": lambda: record_invoice_payment(connection, "sale"),
        "6": lambda: record_invoice_payment(connection, "purchase"),
        "7": lambda: record_expense(connection),
        "8": lambda: show_stock_report(connection),
        "9": lambda: list_open_invoices(connection, "sale"),
        "10": lambda: list_open_invoices(connection, "purchase"),
        "11": lambda: show_invoice_history(connection),
        "12": lambda: show_financial_summary(connection),
        "13": lambda: show_payment_history(connection),
        "14": lambda: show_expense_history(connection),
    }
    try:
        while True:
            show_menu()
            choice = input("Apna intikhab likhein: ").strip()
            if choice == "0":
                print("Hisaab save hai. Allah Hafiz!")
                break
            action = actions.get(choice)
            if action is None:
                print("Ghalat intikhab. Menu mein se 0 se 14 tak chunein.")
                continue
            try:
                action()
            except sqlite3.IntegrityError as error:
                print(f"Database ne entry qabool nahin ki: {error}")
            except ValueError as error:
                print(f"Entry mukammal nahin hui: {error}")
            input("\nMenu par wapas jane ke liye Enter dabayein...")
    except (KeyboardInterrupt, EOFError):
        print("\nProgram band ho raha hai. Pehle se save shuda record mehfooz hain.")
    finally:
        connection.close()
# juat for practice

if __name__ == "__main__":
    main()
