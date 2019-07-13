import os
import sys
import json
import string
import time
import random
import pickle
import threading
import socket
import logging
from datetime import datetime

logging.basicConfig(format='%(asctime)s|%(threadName)s|%(levelname)s:%(message)s', level=logging.ERROR)
logging.getLogger('Peer').setLevel(logging.DEBUG)


T1_UPDATE_TIME = 5 	# 30 seconds
T2_UPDATE_TIME = 5 	# 40 seconds
T3_UPDATE_TIME = 5 	# 1 minute
T4_UPDATE_TIME = 10 # 5 minutes

def load_config(peer_name, config_file='config.json'):
    with open(config_file, 'r') as conf_file:
        conf_json = conf_file.read()
        return json.loads(conf_json)

def random_name():
	return '__folder__' + ''.join(random.choices(string.ascii_uppercase + string.digits, k=20))

class Peer():
	def __init__(self, peer_name):
		self.name = peer_name
		self.logger = logging.getLogger('Peer')

		self._metadata_version = 0

		self.config = load_config(self.name)
		self.network_address = [a for a in  self.config['peers'] if a['name']==self.name][0]
		
		self.network_address = (self.network_address['host'], int(self.network_address['port']))

		self.shared_metadata = {
			peer['name']: {
				'peer': peer['name'],
				'data': {},
				'version': -1
			} for peer in self.config['peers']
		}

		self.last_acknowledge = {
			peer['name']: datetime.now()
			for peer in self.config['peers']
		}

		self.neighbours_peers = {
			peer['name']: peer 
			for peer in self.config['peers'] 
			if peer['name'] != self.name
		}

		self.start()

	def start(self):
		self.logger.info('Peer iniciado com nome [{}] e porta [{}]'.format(self.name, self.network_address))
	
		self.folder_name = self.create_folder()
	
		self.logger.info('Compartilhando pasta [{}]'.format(self.folder_name))
		
		self.metadata = self.get_updated_metadata()

		self.logger.info('dados atualizados para [{}]'.format(self.metadata))

		t1 = threading.Thread(target=self.update_own_metadata, name='Thread-1')
		t2 = threading.Thread(target=self.send_own_data, name='Thread-2')
		t3 = threading.Thread(target=self.send_other_data, name='Thread-3')
		t4 = threading.Thread(target=self.clear_metadata, name='Thread-4')

		t5 = threading.Thread(target=self.metadata_receiver, name='Thread-5')

		t1.start()
		t2.start()
		t3.start()
		t4.start()
		t5.start()

	def clear_metadata(self):
		while True:


			to_delete = [
				k for k, v in self.last_acknowledge.items() 
				if (
						time.mktime(datetime.now().timetuple()) - time.mktime(v.timetuple())
					) > 30 # 1 minuto
			]

			self.logger.info(
				'apagando metadados de peers antigos: {}'.format(to_delete)
			)

			for peer in to_delete:
				self.shared_metadata[peer] = {
					'peer': peer,
					'data': {},
					'version': -1
				}

			time.sleep(T4_UPDATE_TIME)

	def metadata_receiver(self):
		sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
		sock.bind(self.network_address)
		while True:
			raw_data = sock.recvfrom(1024)

			metadata = self._deserialize(raw_data)

			peer_name = metadata['peer']
			version = metadata['version']

			self.logger.info('Recebendo dados do peer {} na versão {}'.format(peer_name, version))

			if version > self.shared_metadata[peer_name]['version']:
				self.last_acknowledge[peer_name] = datetime.now()
				self.shared_metadata[peer_name] = metadata


	def send_other_data(self):
		while True:
			sender_peer_name, metadata = random.choice(list(self.shared_metadata.items()))

			receiver_peer_name, address = random.choice(
				list(self.neighbours_peers.items())
			)

			self.logger.debug(
				'Enviando dados de [{}] para peer sorteado [{}]'.format(
					sender_peer_name, receiver_peer_name
				)
			)

			address = (address['host'], int(address['port']))
			sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
			message = self._serialize(metadata)
			sock.sendto(message, address)

			time.sleep(T3_UPDATE_TIME)



	def update_own_metadata(self):
		while True:
			self.metadata = self.get_updated_metadata()
			self.shared_metadata[self.name] = self.metadata
			self.logger.info(
				'dados atualizados! versão: {version} ; dados: {data}'.format(**self.metadata)
			)

			self.logger.debug(json.dumps(self.shared_metadata, sort_keys=True, indent=4))

			time.sleep(T1_UPDATE_TIME)

			
	def send_own_data(self):
		while True:
			peer_name, address = random.choice(list(self.neighbours_peers.items()))
			
			self.logger.info('Enviando dados próprios para peer sorteado [{}]'.format(peer_name))

			address = (address['host'], int(address['port']))
			sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
			message = self._serialize(self.shared_metadata[self.name])
			sock.sendto(message, address)

			time.sleep(T2_UPDATE_TIME)

	def _serialize(self, dict_):
		return pickle.dumps(dict_)

	def _deserialize(self, message):
		return pickle.loads(message[0])

	def create_folder(self):
		folder_name = random_name()
		try:
			os.mkdir(folder_name)
		except FileExistsError as e:
			self.logger.warning('[{}] já existe! usando-o para compartilhamento'.format(folder_name))

		return folder_name

	def get_updated_metadata(self):
		metadata = list(os.walk(self.folder_name))
		self._metadata_version += 1
		if len(metadata):
			return {
				'data': metadata[0][2], 
				'version': self._metadata_version,
				'peer': self.name
			}
		else:
			return {
				'data': [], 
				'version': self._metadata_version,
				'peer': self.name
			}

if __name__ == '__main__':
	peer_name = sys.argv[1]
	p1 = Peer(peer_name)