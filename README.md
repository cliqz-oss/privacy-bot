# privacy_bot

Privacy Bot aims at giving the tools to collect, store and analyze privacy
policies of the most popular domains on the Internet.

You can find the current privacy policies in the `privacy_policies` folder.

## Ideas

* Some websites require javascript to access the privacy policy (headless
  browser?)
* After we find the URL of the privacy policy for a given domain, we could
  manually validate it and forbid privacy_bot to use any other URL for this
  domain. Privacy bot could notify if the validated URL is not valid.
* Some domains seem to have several pages related to privacy, we could collect
  all of them.
* Some domain have URL with randomly generated parts inside, which will make
  the policy appear like it was updated. We could strip these random parts before
  saving the policy.
* Add even more domains.
* Make use of proxies to have an IP in the country we want.
* Improve parallelism (for a given domain, requests are sequential)
