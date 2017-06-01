#!/bin/bash
case $1 in
    install)
            docker image build privacy_bot_docker/ -t privacy-bot
            ;;
            
    find_policies)
            docker run -v $(pwd)/$2:/tmp/domains.txt privacy-bot sh -c "find_policies --urls /tmp/domains.txt" 
            ;;
            
    fetch_policies)
            docker run -v $(pwd)/$2:/tmp/policy_url_candidates.json privacy-bot sh -c "fetch_policies /tmp/policy_url_candidates.json"
            ;;
esac
