# import pika
# import os
# import json
# import logging
# import time
# from apps.trading.service import TradingService

# # Configure logging
# logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# class RabbitMQConnection:
#     _connection = None

#     @staticmethod
#     def get_connection_with_retry(max_retries=5, retry_delay=10):
#         retry_count = 0
#         while retry_count < max_retries:
#             try:
#                 if RabbitMQConnection._connection is None or RabbitMQConnection._connection.is_closed:
#                     url = os.environ['CLOUDAMQP_URL']
#                     params = pika.URLParameters(url)
#                     params.connection_attempts = 3
#                     params.retry_delay = 5  # Time in seconds to wait before retrying connection
#                     RabbitMQConnection._connection = pika.BlockingConnection(params)
#                 return RabbitMQConnection._connection
#             except pika.exceptions.AMQPConnectionError as error:
#                 if "connection limit" in str(error):
#                     logging.warning("Connection limit reached, retrying in %s seconds...", retry_delay)
#                     time.sleep(retry_delay)
#                     retry_count += 1
#                 else:
#                     logging.error("Failed to connect to RabbitMQ: %s", error)
#                     raise
#         raise Exception("Failed to connect to RabbitMQ after several retries.")

# def start_consumer():
#     connection = None  # Ensure the connection variable is defined
#     try:
#         connection = RabbitMQConnection.get_connection_with_retry()
#         channel = connection.channel()
#         channel.queue_declare(queue='trade_alerts', durable=True)

#         def callback(ch, method, properties, body):
#             data = json.loads(body)
#             try:
#                 TradingService.process_order(data)
#             except Exception as e:
#                 logging.error("Error processing message: %s", e)
#             finally:
#                 ch.basic_ack(delivery_tag=method.delivery_tag)

#         channel.basic_consume(queue='trade_alerts', on_message_callback=callback, auto_ack=False)
#         logging.info('Worker started. Waiting for messages.')
#         channel.start_consuming()
#     except Exception as e:
#         logging.error("An error occurred: %s", e)
#     finally:
#         if connection and not connection.is_closed:
#             connection.close()
#             logging.info("RabbitMQ connection closed.")

# if __name__ == '__main__':
#     start_consumer()
