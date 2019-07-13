# Relatorio Exercicio Programatico 1 - Sistemas Distribuidos

## Objetivo

Crie um programa que permita a um peer trocar mensagens com outros peers via Gossip,
utilizando UDP. A seguir, entenda-se por X, W, Z os identificadores dos peers.

## Estratégia

* Usando Python puro
* Biblioteca ```threading``` nativa do python para gerenciar as threads
* Biblioteca ```sockets``` nativa do python para gerenciar comunicação UDP
* Biblioteca ```pickle``` para serialização dos arquivos trafegados nos pacotes UDP

## Implementação

A ideia dessa implementação era desenvolver um script enxuto que fizesse todas as tarefas basicas desempenhadas por um _peer_ da rede gossip. Tendo a rede conhecida (através de um arquivo _config.json_) um peer deve desempenhar, de maneira paralela, cada umas das atividades listadas:

1. atualizar em memoria metadados de uma pasta relacionada ao peer
2. compartilhar os metadadados do peer para um outro peer aleatorio
3. compartilhar os metadadados de outro peer para um terceiro peer aleatorio
4. apagar metadados muito antigos que não foram atualizados

para o item _1_ foi necessario na inicalização do peer ele gerar uma pasta de nome aleatoria, essa pasta é observada de tempos em tempos (30 segundos) e é capturado metadados (só o nome para fins de teste) e armazenados em um dicionario na mémoria do programa.

```python
	def start(self):
		self.logger.info(
            'Peer iniciado com nome [{}] e porta [{}]'.format(
                self.name, self.network_address
            )
        )
	
		self.folder_name = self.create_folder()
	
		self.logger.info('Compartilhando pasta [{}]'.format(self.folder_name))
		
		self.metadata = self.get_updated_metadata()

        
    def update_own_metadata(self):
		while True:
			self.metadata = self.get_updated_metadata()
			self.shared_metadata[self.name] = self.metadata
			self.logger.info(
				'dados atualizados! versão: {version} ; dados: {data}'.format(**self.metadata)
			)

			self.logger.debug(json.dumps(self.shared_metadata, sort_keys=True, indent=4))

			time.sleep(T1_UPDATE_TIME)
```

Para o item 2 é sorteado um peer (que não seja o próprio) e com esse é feita uma conexão UDP. Para esse caso e o caso 3 foi necessario manter uma quinta thread sempre ativa recebendo qualquer informação que pudesse chegar a um peer. É por essa conexão que enviamos os dados (usando a biblioteca socket e fazendo um _bind_ numa porta especificada pelo _config.json_).

```python
	def send_own_data(self):
		while True:
			peer_name, address = random.choice(list(self.neighbours_peers.items()))
			
			self.logger.info('Enviando dados próprios para peer sorteado [{}]'.format(peer_name))

			address = (address['host'], int(address['port']))
			sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
			message = self._serialize(self.shared_metadata[self.name])
			sock.sendto(message, address)

			time.sleep(T2_UPDATE_TIME)
```

Para o item quatro, sempre que a thread _5_ captura um dado, ela atualiza um dicionario de timestamps. Dessa forma você tem controle de quando foi a ultima atualização do metadado de um certo peer. Dessa forma num dado tempo (5 minutos) apagamos peers com metadados muito antigos.

Para evitar a colisão de dados antigos com novos, sempre que um peer gera seu proprio metadado, ele versiona, começando no -1 (que representa que não houve checagem no arquivo) e vai incrementando. Dessa forma se a thread _5_ recebe um peer desatualizado ela o ignora.
