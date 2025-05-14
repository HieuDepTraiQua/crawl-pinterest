import pika
import json
import asyncio
from typing import List
import logging
from utils.logger import setup_logger
from modules.pinterest import PinterestCrawler
from utils.config import Config

logger = setup_logger(__name__)


class RabbitMQListener:
    def __init__(self):
        self.connection = None
        self.channel = None
        self.crawler = PinterestCrawler()
        self.setup_rabbitmq()

    def setup_rabbitmq(self):
        """Thiết lập kết nối với RabbitMQ"""
        try:
            # Kết nối tới RabbitMQ server
            credentials = pika.PlainCredentials(
                Config.RABBITMQ_CONFIG["username"], Config.RABBITMQ_CONFIG["password"]
            )
            parameters = pika.ConnectionParameters(
                host=Config.RABBITMQ_CONFIG["host"],
                port=Config.RABBITMQ_CONFIG["port"],
                credentials=credentials,
            )
            self.connection = pika.BlockingConnection(parameters)
            self.channel = self.connection.channel()

            # Khai báo queue
            self.channel.queue_declare(
                queue=Config.RABBITMQ_CONFIG["queue_name"], durable=True
            )

            logger.info("Đã kết nối thành công với RabbitMQ")
        except Exception as e:
            logger.error(f"Lỗi khi kết nối với RabbitMQ: {e}")
            raise

    async def process_message(self, usernames: List[str]):
        """Xử lý message nhận được từ RabbitMQ"""
        try:
            logger.info(f"Đang lấy thông tin người dùng với {len(usernames)} usernames")
            await self.crawler.crawl_user_profile_by_username(usernames)
        except Exception as e:
            logger.error(f"Lỗi khi xử lý message: {e}")

    def callback(self, ch, method, properties, body):
        """Callback function được gọi khi nhận được message"""
        try:
            # Parse message từ JSON
            message = json.loads(body)
            usernames = message["body"]["username"]
            if not usernames:
                logger.warning("Message không chứa usernames")
                ch.basic_ack(delivery_tag=method.delivery_tag)
                return

            # Chạy async function trong event loop
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            loop.run_until_complete(self.process_message(usernames))
            loop.close()

            # Xác nhận đã xử lý message thành công
            ch.basic_ack(delivery_tag=method.delivery_tag)
            logger.info(f"Đã xử lý xong message với {len(usernames)} usernames")

        except Exception as e:
            logger.error(f"Lỗi khi xử lý callback: {e}")
            # Nếu có lỗi, message sẽ được đưa vào dead letter queue
            ch.basic_nack(delivery_tag=method.delivery_tag)

    def start_listening(self):
        """Bắt đầu lắng nghe messages từ RabbitMQ"""
        try:
            # Thiết lập QoS
            self.channel.basic_qos(prefetch_count=1)

            # Bắt đầu consume messages
            self.channel.basic_consume(
                queue=Config.RABBITMQ_CONFIG["queue_name"],
                on_message_callback=self.callback,
            )

            logger.info("Bắt đầu lắng nghe messages từ RabbitMQ...")
            self.channel.start_consuming()

        except Exception as e:
            logger.error(f"Lỗi khi lắng nghe messages: {e}")
            if self.connection and not self.connection.is_closed:
                self.connection.close()

    def stop(self):
        """Dừng listener và đóng kết nối"""
        if self.connection and not self.connection.is_closed:
            self.connection.close()
            logger.info("Đã đóng kết nối với RabbitMQ")


def main():
    listener = RabbitMQListener()
    try:
        listener.start_listening()
    except KeyboardInterrupt:
        logger.info("Đang dừng listener...")
        listener.stop()


if __name__ == "__main__":
    main()
