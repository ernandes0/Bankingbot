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
