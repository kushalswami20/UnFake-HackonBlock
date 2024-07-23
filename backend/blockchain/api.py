import datetime
import json
import os
import dotenv
from PIL import Image
from web3 import Web3
from fastapi import APIRouter
from pydantic import BaseModel
from brownie import project, network, accounts, Contract
from brownie.project import get_loaded_projects
from brownie.network.account import LocalAccount

from blockchain.certificate import create_certificate
from unmask.unmasker import unmask_image
from utils import file_to_sha256

dotenv.load_dotenv()
bchain_router = APIRouter(tags=['bchain'])

p = project.load('blockchain/brown')
network.connect('polygon-zkevm-testnet')

SimpleCollectible = p.SimpleCollectible
get_loaded_projects()[0].load_config()
print(get_loaded_projects()[0])


def get_account() -> LocalAccount:
    return accounts.add(os.environ.get('PRIVATE_KEY'))


account = get_account()
print(account)


def get_or_deploy_contract():
    # simple_collectible = SimpleCollectible.deploy({"from": account, "gas_price": Web3.to_wei("3", "gwei")})
    deploy_file = 'deployed_address.txt'
    if os.path.exists(deploy_file):
        with open(deploy_file, 'r') as f:
            contract_address = f.read().strip()
        print(f"Loading existing contract at {contract_address}")
        return Contract.from_abi("SimpleCollectible", contract_address, SimpleCollectible.abi)
    else:
        print("Deploying new contract")
        contract = SimpleCollectible.deploy({"from": account, "gas_price": Web3.to_wei("3", "gwei")})
        with open(deploy_file, 'w') as f:
            f.write(contract.address)
        return contract


simple_collectible = get_or_deploy_contract()

account = get_account()


class PostData(BaseModel):
    user_address: str
    file_uid: str
    transction_id: str = 'xxx'


nft_url = "https://cardona-zkevm.polygonscan.com/nft/{}/{}"


@bchain_router.post('/mint_certificate')
async def mint_certificate(post_data: PostData):
    prediction = unmask_image(Image.open(f'assets/{post_data.file_uid}'))
    file_hash = file_to_sha256(f'assets/{post_data.file_uid}')
    client_address = post_data.user_address

    certificate_id = create_certificate(round(prediction.get('real'), 2) * 100, round(prediction.get('fake'), 2) * 100,
                                        file_hash,
                                        client_address,
                                        simple_collectible.address, datetime.datetime.now().date())
    certificate_url = 'https://pet-bird-precisely.ngrok-free.app/certificate/' + certificate_id
    uri = {
        "name": f"Deep Fake Certification",
        "description": f"Deep Fake Certification",
        "image": certificate_url,
        "file_hash"
        "attributes": [
            prediction
        ]
    }
    json_uri = json.dumps(uri)
    # tx = web3.eth.get_transaction(post_data.transction_id)
    # client_address = tx.get('from')
    # print(client_address, tx)

    tx = simple_collectible.createCollectible(json_uri, client_address,
                                              {"from": account, "gas_price": Web3.to_wei("3", "gwei")})

    # Wait for the transaction to be mined
    tx.wait(1)

    # Get the token ID of the newly minted token
    token_id = simple_collectible.tokenCounter() - 1

    # Get the token URI
    uri = simple_collectible.tokenURI(token_id)

    nft_url_formatted = nft_url.format(simple_collectible.address, token_id)

    return {
        "polygon_url": nft_url_formatted,
        'certificate_url': certificate_url,
        'token_id': token_id,
        'token_uri': uri
    }


@bchain_router.get('/cert/{user_address}')
async def get_user_nfts(user_address: str):
    try:
        # Get the total supply of tokens
        total_supply = simple_collectible.totalSupply()

        # Initialize an empty list to store the user's NFTs
        user_nfts = []

        # Iterate through all tokens
        for token_id in range(total_supply):
            # Check if the current user is the owner of this token
            if simple_collectible.ownerOf(token_id) == user_address:
                # If yes, get the token URI and add it to the list
                uri = simple_collectible.tokenURI(token_id)

                user_nfts.append(
                    {"token_id": token_id, "uri": json.loads(uri),
                     "polygon_url": nft_url.format(simple_collectible.address, token_id)})
        return {"user_address": user_address, "nfts": user_nfts}
    except Exception as e:
        return {"error": f"Error getting user NFTs: {str(e)}"}


@bchain_router.get('/get_token_uri/{token_id}')
async def get_token_uri(token_id: int):
    try:
        if not simple_collectible:
            return {"error": "Contract not deployed"}
        uri = simple_collectible.tokenURI(token_id)
        return {"token_id": token_id, "uri": json.loads(uri)}
    except Exception as e:
        return {"error": f"Error getting tokenURI: {str(e)}"}
