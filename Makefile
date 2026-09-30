SSH        := ssh -F ssh_config
REMOTE     := vpn
REMOTE_DIR := /opt/vpn-service
GIT_SSH    := ssh -i .secrets/github_deploy_ed25519 -o IdentitiesOnly=yes -o UserKnownHostsFile=.secrets/known_hosts -o StrictHostKeyChecking=accept-new

.PHONY: ssh deploy logs ps restart test push bootstrap

ssh:            ## open a shell on the server
	$(SSH) $(REMOTE)

bootstrap:      ## one-time server setup (docker, fail2ban, bbr, firewall)
	$(SSH) $(REMOTE) 'bash -s' < scripts/bootstrap.sh

deploy:         ## sync code and (re)start containers
	$(SSH) $(REMOTE) 'mkdir -p $(REMOTE_DIR)'
	rsync -az --delete -e "$(SSH)" \
	  --exclude .git --exclude .secrets --exclude .env --exclude '__pycache__' --exclude '.pytest_cache' --exclude data \
	  ./ $(REMOTE):$(REMOTE_DIR)/
	$(SSH) $(REMOTE) 'cd $(REMOTE_DIR) && docker compose -p vpn-service up -d --build --remove-orphans && docker compose -p vpn-service ps'

logs:
	$(SSH) $(REMOTE) 'cd $(REMOTE_DIR) && docker compose -p vpn-service logs --tail=100 -f'

ps:
	$(SSH) $(REMOTE) 'cd $(REMOTE_DIR) && docker compose -p vpn-service ps'

restart:
	$(SSH) $(REMOTE) 'cd $(REMOTE_DIR) && docker compose -p vpn-service restart'

test:
	cd bot && python3 -m pytest -q

push:           ## push using the repo-scoped deploy key (no password)
	GIT_SSH_COMMAND="$(GIT_SSH)" git push origin HEAD
