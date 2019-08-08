import os
import sys
import json
import pickle
import socket
import random
import string
import shutil
import logging
import threading

logging.basicConfig(format='%(asctime)s|%(threadName)s|%(levelname)s:%(message)s', level=logging.ERROR)
logging.getLogger('Client').setLevel(logging.DEBUG)

def load_config(config_file='config.json'):
    with open(config_file, 'r') as conf_file:
        conf_json = conf_file.read()
        return json.loads(conf_json)

def random_name():
	return '__folder__client__' + ''.join(random.choices(string.ascii_uppercase + string.digits, k=20))


WAIT_FOR_ANSWER_TIMEOUT = 60 # 1 minute

class Client():
	def __init__(self, client_id):

		self.client_id = client_id

		self.logger = logging.getLogger('Client')

		self.config = load_config()

		self.network_address = (self.config['client']['host'], int(self.config['client']['port']))

		self.known_peers = {
			peer['name']: peer 
			for peer in self.config['peers'] 
		}

		self.start()

	def metadata_receiver(self):
		sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
		sock.bind(self.network_address)
		while True:
			raw_data = sock.recvfrom(1024)

			metadata = self._deserialize(raw_data)

			peer_name = metadata['peer']

			self.actual_file_address = (
				self.known_peers[peer_name]['host'],
				self.known_peers[peer_name]['port']
			)

			download_t = threading.Thread(target=self.recv_file, name='download_t')

			download_t.start()


	def start(self):
		self.folder_name = self.create_folder()

		t1 = threading.Thread(target=self.metadata_receiver, name='receiver')
		t1.start()


	def create_folder(self):
		folder_name = random_name()
		try:
			os.mkdir(folder_name)
		except FileExistsError as e:
			self.logger.warning('[{}] já existe! usando-o para compartilhamento'.format(folder_name))

		return folder_name

	def recv_file(self):
		sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

		sock.connect(self.actual_file_address)

		with open('downloaded_file.mp4', 'wb') as f:
		    while True:
		        print('receiving data...')
		        data = s.recv(1024)
		        if not data:
		            break
		        f.write(data)

	def request_file(self, filename):
		random_peer, address = random.choice(list(self.known_peers.items()))


		address = (address['host'], int(address['port']))
		sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

		message = self._serialize(
			{
				'filename': filename, 
				'address': self.network_address, 
				'ttl': 3
			}
		)
		sock.sendto(message, address)

	def _serialize(self, dict_):
		return pickle.dumps(dict_)

	def _deserialize(self, message):
		return pickle.loads(message[0])

	def _input_manager(self):
		while True:
			message = input('Qual arquivo você quer encontrar?')

			self.logger.info('Buscando por arquivo [{}]...'.format(message))
			found = self.request_file(message)
			if found:
				continue
			else:
				self.logger.info('Não achei seu arquivo :(')



if __name__ == '__main__':
	client_id = sys.argv[1]
	c1 = Client(client_id)

	c1._input_manager()




