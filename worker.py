# Railway uchun alohida worker kerak bo‘lsa ishlatiladi.
# Hozir MVP bitta process ichida bot + queue + worker sifatida ishlaydi.
from main import main
import asyncio

if __name__ == "__main__":
    asyncio.run(main())
