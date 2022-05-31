<h1 align="center"> BankingBot </h1>

<p align="center">🚀 O BankingBot é uma aplicação em desenvolvimento para a disciplina: Projeto Interdisciplinar para Sistemas de Informação IV do curso de Sistemas de Informação na Universidade Federal Rural de Pernambuco. O Bot tem o intuito de simular cadastros e consultas bancárias por meio de um chat em texto.</p>

<p align="center">O desenvolvimento do bot foi realizado inteiramente na plataforma em nuvem Amazon Web Services(AWS), com o auxílio das tecnologias Amazon Lambda, DynamoDB e Amazon Lex.</p>

<h1 align="center"> Descrição e demonstração </h1>

<p align="center"> O Bot foi criado e configurado no Lex Console. Lá é definido as intents do bot e o fluxo de conversação. </p>

![image](https://user-images.githubusercontent.com/103939290/171082858-b8b4370d-5ea5-4cab-82b4-bc726d89c980.png)
![image](https://user-images.githubusercontent.com/103939290/171082920-37195c85-5e14-4c71-af0a-3f81f22405ae.png)
![image](https://user-images.githubusercontent.com/103939290/171081060-d8979a3d-f89c-4a52-a3b4-2e13c2ee81be.png)
![image](https://user-images.githubusercontent.com/103939290/171081788-f9b2168e-d164-4198-8d8c-e6a159ea6b3e.png)

<p align="center"> As informações digitadas pelo usuário no momento da criação da conta ficam salvas no DynamoDB.</p>

![image](https://user-images.githubusercontent.com/103939290/171082262-6d0179a9-bf14-4584-a906-67b05672b669.png)

<p align="center"> Para a conexão entre os dois serviços foi utilizada uma função Lambda, a qual define algumas condicionais para os dados digitados e realiza a inserção no banco. </p>

``` python
import json
import os
import dateutil.parser
import logging
import boto3
import uuid
import time
import datetime

logger = logging.getLogger()
logger.setLevel(logging.DEBUG)

dyn_client = boto3.client('dynamodb')
TABLE_NAME = "Bank"

def safe_int(n):
    if n is not None:
        n = int(n)
        return n
    return n
    
def try_ex(value):
    
    if value is not None:
        return value['value']['interpretedValue']
    else:
        return None
        
def elicit_slot(session_attributes, active_contexts, intent, slot_to_elicit, message):
    return {
        'sessionState': {
            'activeContexts':[{
                'name': 'intentContext',
                'contextAttributes': active_contexts,
                'timeToLive': {
                    'timeToLiveInSeconds': 600,
                    'turnsToLive': 1
                }
            }],
            'sessionAttributes': session_attributes,
            'dialogAction': {
                'type': 'ElicitSlot',
                'slotToElicit': slot_to_elicit
            },
            'intent': intent,
            'messages': [{
                    'contentType': 'PlainText',
                    'content': message
            }]
        }
    }
    
    
def confirm_intent(active_contexts, session_attributes, intent, message):
    return {
        'sessionState': {
            'activeContexts': [active_contexts],
            'sessionAttributes': session_attributes,
            'dialogAction': {
                'type': 'ConfirmIntent'
            },
            'intent': intent,
            'messages': [{
                'contentType': 'PlainText',
                'content': message
            }]
        }
    }
    
    

def get_session_attributes(intent_request):
    try:
        return intent_request['sessionState']['sessionAttributes']
    except:
        return {}

def close(session_attributes, active_contexts, fulfillment_state, intent, message):
    response = {
        'sessionState': {
            'activeContexts':[{
                'name': 'intentContext',
                'contextAttributes': active_contexts,
                'timeToLive': {
                    'timeToLiveInSeconds': 600,
                    'turnsToLive': 1
                }
            }],
            'sessionAttributes': session_attributes,
            'dialogAction': {
                'type': 'Close',
            },
            'intent': intent,
            'messages': [message]
        }
    }

    return response
    
def delegate(session_attributes, active_contexts, intent, message):
    return {
        'sessionState': {
            'activeContexts':[{
                'name': 'intentContext',
                'contextAttributes': active_contexts,
                'timeToLive': {
                    'timeToLiveInSeconds': 600,
                    'turnsToLive': 1
                }
            }],
            'sessionAttributes': session_attributes,
            'dialogAction': {
                'type': 'Delegate',
            },
            'intent': intent,
            'messages': [message]
        }
    }
    
def save_bank(firstName, phone, balance, user):
    id = str(uuid.uuid4())
    
    data = dyn_client.put_item(
        TableName = TABLE_NAME,
        Item = {
            'id': {
                'S': id
            },
            'first_name': {
                'S': firstName
            },
            'balance': {
                'N': str(balance)
            },
            'phone': {
                'S': phone
            },
            'user': {
                'S': user
            }
        }
    )

    
def validate_bank(slots):
    first_name = try_ex(slots['Name'])
    phone = try_ex(slots['Phonenumber'])
    user = try_ex(slots['Username'])
    balance = safe_int(try_ex(slots['Balance']))
        
    if balance is not None and(balance < 1 or balance > 100000000000):
        return build_validation_result(
            False,
            'Balance',
            'Seja realista, seu saldo deve ser entre 1 e 100000000000. Digite o saldo novamente.'
        )
            
    return{'isValid': True}
    
def build_validation_result(isvalid, violated_slot, message_content):
    return{
        'isValid': isvalid,
        'violatedSlot': violated_slot,
        'message': message_content
    }
    
def take_bank(intent_request):
    slots =  intent_request['sessionState']['intent']['slots']
    first_name = slots['Name']
    phone = slots['Phonenumber']
    user = slots['Username']
    balance = slots['Balance']

    confirmation_status = intent_request['sessionState']['intent']['confirmationState']
    session_attributes = get_session_attributes(intent_request)
    active_contexts = {}
    
    logger.debug(intent_request['invocationSource'])
    
    if intent_request['invocationSource'] == 'DialogCodeHook':
        
        validation_result = validate_bank(intent_request['sessionState']['intent']['slots'])
        logger.debug(validation_result)
        if not validation_result['isValid']:
            slots[validation_result['violatedSlot']] = None
            return elicit_slot(
                session_attributes,
                active_contexts,
                intent_request['sessionState']['intent']['name'],
                validation_result['violatedSlot'],
                validation_result['message']
            )
        
        if confirmation_status == 'None':
            return delegate(session_attributes, active_contexts, intent_request['sessionState']['intent'], 'message')

        elif confirmation_status == 'Confirmed':
            saveName = try_ex(first_name)
            savePhone = try_ex(phone)
            saveBalance = try_ex(balance)
            saveUser = try_ex(user)
            logger.debug(saveName)
            save_bank(saveName, savePhone, saveBalance, saveUser)
    
            return close(
                session_attributes,
                active_contexts,
                'Fulfilled',
                intent_request['sessionState']['intent'],
                        {
                            'contentType': 'PlainText',
                            'content': 'Obrigado{}, nós salvamos seu cadastro!.'.format(saveName)
                        }
                        )
    
def dispatch(intent_request):
    logger.debug('dispatch userId={}, intentName={}'.format(intent_request['sessionId'], intent_request['sessionState']['intent']['name']))
    intent_name = intent_request['sessionState']['intent']['name']
    
    if intent_name == 'BankCreateAcc':
        return take_bank(intent_request)
        
    raise Exception('Intent with name' + intent_name + 'not supported')
    
def lambda_handler(event, context):
    os.environ['TZ'] = 'America/New_York'
    time.tzset()
    logger.debug('event.bot.name={}'.format(event['bot']['name']))
    return dispatch(event)
```

<h3> 
	🚧  Em construção...  🚧
</h3>

### Funcionalidades
- [X] Cadastro de Usuários
- [ ]  Consulta de saldo

### - [Amazon Web Services](https://aws.amazon.com)

Amazon Web Services, também conhecido como AWS, é uma plataforma de serviços de computação em nuvem, que formam uma plataforma de computação na nuvem oferecida pela Amazon.com. Os serviços são oferecidos em várias áreas geográficas distribuídas pelo mundo.

### - [Amazon Lambda](https://aws.amazon.com/pt/lambda/?nc2=h_ql_prod_fs_lbd)

O AWS Lambda é um serviço de computação sem servidor e orientado a eventos que permite executar código para praticamente qualquer tipo de aplicação ou serviço de backend sem provisionar ou gerenciar servidores. Você pode acionar o Lambda a partir de mais de 200 serviços da AWS e aplicações de software como serviço (SaaS) e pagar apenas pelo que usar.

![image](https://user-images.githubusercontent.com/103939290/171079080-1c0758f0-6f28-48d7-845d-a39f03286c74.png)


### - [DynamoDB](https://aws.amazon.com/pt/dynamodb/?nc2=h_ql_prod_db_ddb)

O Amazon DynamoDB é um banco de dados de chave-valor NoSQL, sem servidor e totalmente gerenciado, projetado para executar aplicações de alta performance em qualquer escala. O DynamoDB oferece segurança integrada, backups contínuos, replicação multirregional automatizada, armazenamento em cache na memória e ferramentas de exportação de dados.

![image](https://user-images.githubusercontent.com/103939290/171079034-2532b808-7a61-4a0f-a439-6cf44f0e9c90.png)


### - [Amazon Lex](https://aws.amazon.com/pt/lex/?nc2=h_ql_prod_ml_lex)

O Amazon Lex V2 é um serviço da AWS para a criação de interfaces de conversa para aplicativos que usam voz e texto. O Amazon Lex V2 fornece a funcionalidade e a flexibilidade avançadas de compreensão de linguagem natural (NLU) e o reconhecimento automático de fala (ASR) para permitir a criação de experiências do usuário altamente envolventes com interações por conversa realistas e a criação de novas categorias de produtos.

O Amazon Lex V2 permite que qualquer desenvolvedor crie bots de conversa rapidamente. Com o Amazon Lex V2, nenhuma experiência em deep learning é necessária — para criar um bot, você especifica o fluxo de conversa básico no console do Amazon Lex V2. O Amazon Lex V2 gerencia a caixa de diálogo e ajusta dinamicamente as respostas na conversa. Usando o console, você pode criar, testar e publicar o chatbot de texto ou voz. Em seguida, você pode adicionar as interfaces de conversa aos bots em dispositivos móveis, aplicativos Web e plataformas de bate-papo (por exemplo, Facebook Messenger).

![image](https://user-images.githubusercontent.com/103939290/171078902-c7ba4285-5459-4adb-8c9d-54727d8505ec.png)
