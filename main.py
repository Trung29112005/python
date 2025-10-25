# Yêu cầu cài đặt thêm các thư viện:
# pip install httpx pytz apscheduler
from keep_alive import keep_alive
keep_alive()
from zalo_bot import Update
# Import các lớp cần thiết
from zalo_bot.ext import ApplicationBuilder, CommandHandler, ContextTypes 
from datetime import time
import pytz
import httpx
import asyncio 
# Sử dụng BackgroundScheduler
from apscheduler.schedulers.background import BackgroundScheduler 

# --- KHU VỰC CẤU HÌNH TỐI GIẢN ---
# Chat ID cần gửi tin nhắn (Giữ nguyên tên biến)
# LƯU Ý QUAN TRỌNG: VUI LÒNG KIỂM TRA CHẮC CHẮN RẰNG ID NÀY LÀ HỢP LỆ (ID CỦA BẠN HOẶC NHÓM MÀ BOT ĐÃ ĐƯỢC THÊM VÀO)
chat_1 = '7badb9422317ca499306' 

# Danh sách UID cần request (Người dùng cài số lượng: 2-3 hoặc nhiều hơn)
USER_UIDS = [
    #"UID_THU_NHAT_CUA_BAN", # <-- HÃY THAY THẾ UID CỦA BẠN VÀO ĐÂY ĐỂ TEST
    #"UID_THU_HAI_CUA_BAN", 
    "856575392",
    "11976170309"
] 

# URL API
API_URL_TEMPLATE = "https://ff.mlbbai.com/like/?key=emon&uid={}"

# Thiết lập múi giờ TP. Hồ Chí Minh và THỜI GIAN CHẠY TEST (15:23)
HCMC_TIMEZONE_NAME = 'Asia/Ho_Chi_Minh'
HCMC_TIMEZONE = pytz.timezone(HCMC_TIMEZONE_NAME)
SCHEDULE_TIME = time(07, 00, 0) # THỜI GIAN CHẠY TỰ ĐỘNG: 15:23:00 hàng ngày

# Hàm BẤT ĐỒNG BỘ: Thực hiện request và gửi kết quả
async def daily_like_fetch_task(bot, chat_id) -> None:
    """Thực hiện request cho tất cả UID và gửi kết quả về chat_1."""
    
    results = []
    
    # Sử dụng httpx để thực hiện request bất đồng bộ
    async with httpx.AsyncClient(timeout=30.0) as client:
        # 1. Tạo danh sách các tác vụ (task) request
        tasks = []
        for uid in USER_UIDS:
            url = API_URL_TEMPLATE.format(uid)
            tasks.append(client.get(url))
        
        # 2. Chạy đồng thời tất cả các request
        responses = await asyncio.gather(*tasks, return_exceptions=True)

        # 3. Xử lý kết quả trả về từ từng request
        for uid, response in zip(USER_UIDS, responses):
            if isinstance(response, Exception):
                results.append(f"UID {uid} (LỖI KẾT NỐI): {response.__class__.__name__}")
                continue

            try:
                # Kiểm tra lỗi HTTP (ví dụ: 404, 500)
                response.raise_for_status() 
                data = response.json() 
                results.append(f"UID {uid} (Thành công): {data}")
            except httpx.HTTPStatusError as e:
                results.append(f"UID {uid} (Lỗi HTTP {e.response.status_code}): {e.response.text.strip()}")
            except Exception as e:
                results.append(f"UID {uid} (Lỗi Xử Lý Data): {e}")

    # Tổng hợp data 
    data_lay_duoc = f"KẾT QUẢ REQUEST TỰ ĐỘNG ({SCHEDULE_TIME.strftime('%H:%M')} HCMC):\n\n" + "\n---\n".join(results)
    
    # --- LOGGING VÀ GỬI TIN NHẮN ĐƯỢC TĂNG CƯỜNG ---
    print(f"⏳ Đang cố gắng gửi tin nhắn tới Chat ID: {chat_id}")
    try:
        await bot.send_message(chat_id, data_lay_duoc)
        print(f"✅ Đã gửi kết quả thành công tới {chat_id}")
    except Exception as e:
        # In ra lỗi chi tiết từ Zalo API (nếu có)
        print(f"❌ LỖI KHI GỬI TIN NHẮN TỚI {chat_id}: {e}")
        print(f"💡 HƯỚNG DẪN: Hãy kiểm tra lại CHAT ID ({chat_id}) và chắc chắn bot đã được THÊM vào nhóm chat/là bạn bè.")
    # --- KẾT THÚC LOGGING ---


# Hàm ĐỒNG BỘ: Tạo cầu nối để gọi hàm async bên trong BackgroundScheduler
def daily_like_fetch_wrapper(bot, chat_id):
    """
    Hàm wrapper đồng bộ để gọi daily_like_fetch_task bất đồng bộ.
    Đã sửa lỗi RuntimeError bằng cách tạo Event Loop mới.
    """
    print(f"⚙️ Bắt đầu chạy daily_like_fetch_wrapper.")
    
    # --- PHẦN SỬA LỖI RuntimeError: There is no current event loop ---
    loop = None 
    try:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        
        # Chạy hàm async và chờ nó hoàn thành
        loop.run_until_complete(daily_like_fetch_task(bot, chat_id))
        
    except Exception as e:
        print(f"❌ LỖI TRONG SCHEDULER THREAD: Không thể chạy tác vụ bất đồng bộ: {e}")
        
    finally:
        if loop and not loop.is_closed():
             loop.close()
        print("✅ daily_like_fetch_wrapper hoàn tất và Event Loop đã đóng.")
    # --- KẾT THÚC PHẦN SỬA LỖI ---


# Hàm xử lý cho lệnh /start
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await update.message.reply_text(f"Chào {update.effective_user.display_name}! Tôi là bot like FF! 🤖, ")

# Hàm xử lý cho lệnh /echo
async def echo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    message = " ".join(context.args)
    if message:
        await update.message.reply_text(f"Bạn vừa nói: {message}")
    else:
        await update.message.reply_text("Hãy nhập gì đó sau lệnh /echo")

if __name__ == "__main__":
    # --- APP BUILDER ---
    app = ApplicationBuilder().token("2839373401838259358:FilebUWuMBRmmaJToUgOsycnHcpnWSMbrUVFlBwcHiBYUGIQpoEVvxCGjxztdbrI").build()
    # --- KẾT THÚC CẤU HÌNH ---

    # Khởi tạo BackgroundScheduler
    scheduler = BackgroundScheduler(timezone=HCMC_TIMEZONE_NAME)
    
    # Thêm công việc chạy hàm wrapper (đồng bộ) hàng ngày lúc 15:23
    scheduler.add_job(
        daily_like_fetch_wrapper, 
        'cron', 
        hour=SCHEDULE_TIME.hour,        
        minute=SCHEDULE_TIME.minute,      
        args=[app.bot, chat_1], 
        id='daily_like_job'
    )

    # Khởi động bộ lên lịch ngay trước khi bot chạy polling
    scheduler.start()
    print(f"✅ Scheduler đã khởi động và lên lịch chạy lúc {SCHEDULE_TIME.strftime('%H:%M')} HCMC.")
    
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("echo", echo))

    print("🤖 Bot siêu cấp vip đang chạy...")
    app.run_polling()
