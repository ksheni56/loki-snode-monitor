# Loki Service Node Monitor and Email Alert

import os
import sys
import requests
import time
from dotenv import load_dotenv
import logging
import status_logger
import yagmail
from node_list import snode_list, remote_node_list

load_dotenv()

# ENV VARS
FROM = os.getenv('FROM_ADDRESS')
FROM_PASS = os.getenv('FROM_PASS')
TO = os.getenv('TO_ADDRESS')

# Initialize Yagmail
yag = yagmail.SMTP(FROM, FROM_PASS)


def node_selector(node_list):
    """Connect to a Loki remote node to get service node uptime data."""
    for x in node_list:    
        try:
            r = requests.get(x, timeout=10)
            if r.status_code == 200:
                node = x
                pass
            else:
                node = None
            return node
        except KeyboardInterrupt:
            sys.exit()
        except requests.exceptions.Timeout as e:
            status_logger.logger.exception("Exception occured\n")
            time.sleep(60)
            status_logger.logger.info("Reconnecting...")
            continue
        except Exception as e:
            status_logger.logger.exception("Exception occured\n")

def snode_checker(snode_list, url):
    """Check our service node(s) uptime proofs and calculate time delta
    since last uptime proof received."""
    for i in range(len(snode_list)):
        try:

            status_logger.logger.info(f"Checking SNode: {snode_list[i]}")

            # Get SNode data.		
            sns = requests.post(url, json={"jsonrpc":"2.0","id":"0","method":"get_service_nodes", \
            "params": {"service_node_pubkeys": [snode_list[i]]}}, timeout=10).json()

            # Get SNode last uptime proof from SNode data.
            snlup = sns['result']['service_node_states'][0]['last_uptime_proof']
            snlup_time = time.strftime('%b %d, %Y - %I:%M:%S %p', time.localtime(snlup))

            status_logger.logger.info(f"Your Loki Service Node's last uptime proof was received at: {snlup_time}")

            # Get monitor server's current time.
            current_timestamp = int(time.time())
            current_time = time.strftime('%b %d, %Y - %I:%M:%S %p', time.localtime(current_timestamp))

            status_logger.logger.info(f"The monitor server's current time is: {current_time}")

            # Compute time delta between current time and last uptime
            uptime_proof_age = current_timestamp - snlup
            if uptime_proof_age > 3960:
                status_logger.logger.warning(f"Service Node uptime proof is over one hour and six minutes old. Check on the following Service Node immediately: {snode_list[i]}")

                uptime_warning_subject = "URGENT: Loki Service Node Uptime Proof not received"

                uptime_warning_body = f"Your Loki Service Node uptime proof was last accepted by the network at {snlup_time}, over {uptime_proof_age} seconds ago.\n\nCheck on the following Service Node immediately:\n\n{snode_list[i]}"

                yag.send(TO, uptime_warning_subject, uptime_warning_body)
            else:
                status_logger.logger.info(f"Loki service node operational. Last uptime proof accepted at: {snlup_time}. Last uptime proof accepted {uptime_proof_age} seconds ago.")
        except KeyboardInterrupt:
            sys.exit()
        except requests.exceptions.Timeout as e:
            status_logger.logger.exception("Exception occured\n")
            time.sleep(60)
            try:
                status_logger.logger.info("Reconnecting...")
                url = node_selector(remote_node_list)
                if url == None:
                    status_logger.logger.warning("Unable to connect to a Loki remote node.")

                    no_node_subj = "Unable to connect to a Loki remote node."

                    no_node_body = "Unable to connect to a Loki remote node. No nodes in your node list were available. Your service node monitor has stopped. Please investigate the issue."

                    yag.send(TO, no_node_subj, no_node_body)

                    raise TypeError("Unable to connect to a Loki remote node. Remote node cannot be 'None'.")
                else:
                    status_logger.logger.info(f"Connected to: {url}")
            except TypeError as error:
                status_logger.logger.exception("Exception occured\n")
                sys.exit()
            except Exception as e:
                status_logger.logger.exception("Exception occured\n")
    time.sleep(300)


if __name__ == "__main__":

    while True:
        try:
            url = node_selector(remote_node_list)
            if url == None:
                status_logger.logger.warning("Unable to connect to a Loki remote node.")
                no_node_subj = "Unable to connect to a Loki remote node."

                no_node_body = "Unable to connect to a Loki remote node. No nodes in your node list were available. Your service node monitor has stopped. Please investigate the issue."

                yag.send(TO, no_node_subj, no_node_body)

                raise TypeError("Unable to connect to a Loki remote node. Remote node cannot be 'None'.")
            else:
                status_logger.logger.info(f"Connected to: {url}")
                status_logger.logger.info("Getting your Loki Service Node last uptime proof.")
        except KeyboardInterrupt:
            sys.exit()
        except TypeError as error:
            status_logger.logger.exception("Exception occured\n")
            sys.exit()
        except Exception as e:
            status_logger.logger.exception("Exception occured\n")

        try:
            snode_checker(snode_list, url)
        except KeyboardInterrupt:
            sys.exit()
        except Exception as e:
            status_logger.logger.exception("Exception occured\n")