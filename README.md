# :balloon: Privacy Bot

Privacy policies are a legal requirement for websites handling users' data. So anyone should be able to access them, read them and understand what it takes (in terms of privacy) to be using a given service. Except no one reads them  :see_no_evil: . User's fault? Probably not. We can list several reasons:

1. A lot of people don't even know what they are.  :question:
2. They are "legal documents", and it takes a specific set of skills to comprehend them. :scream:
3. They are long and reading them would be time consuming (the median length is ~2500 words).  :zzz:

In short, they don't seem to be designed for people to read and understand. But still, the content of these policies is very important to anyone's privacy, for this is where you should learn what private data you agree to give away.

*Privacy Bot* is a project which aims at addressing aforementioned issues. If policies are not meant for humans, then maybe we can design a bot to automatically do the heavy lifting for us. The high level goals of the project are to:

1. :squirrel: Discover the privacy policy of any domain.
2. :floppy_disk: Automatically fetch and store them in a central place (eg: in a github repository, which will give us `diffs` on updates for free).
3.  :mag: Analyze them to extract a summary of what private data is shared, and with whom.
4. :eyes: Stay up-to-date by monitoring updates.
5. :package: Make all the policies available in a central repository, in a usable data format that people can build upon (eg: building a browser extension to show the summary on any visited website, creating a twitter bot to communicate facts and updates about policies, etc.).

## Privacy policies

You can find the current privacy policies in the `privacy_policies` folder. In
the future, we should probably host them on a separate branch to not mix the
code and the data.

## Getting started

To get going with the project as a contributor, it is recommended to install the
package in 'developer mode' using `pip`, in a virtual environment. You also need
`Python 3`.

```sh
$ pip install -e .
```

There are two entry points, used respectively for:
1. Automagically discovering privacy policies given a list of domains
2. Fetching privacy policies given the output of the first entry point (a list of
   privacy policies for each domain).

```sh
$ find_policies --urls domains.txt
# Outputs: policy_url_candidates.json
$ fetch_policies policy_url_candidates.json
# Outputs: index.json and privacy_policies/
```

Keep in mind that the file formats are still a work in progress, and will likely
evolve in a near future. Feel free to contribute with ideas and improvements!

## Contributing

Thanks for your interest in contributing to *Privacy Bot*! There are many ways to contribute. To get started, take a look at [CONTRIBUTING.md](CONTRIBUTING.md).

## Participation Guidelines

This project adheres to a [code of conduct](CODE_OF_CONDUCT.md). By participating, you are expected to uphold this code. Please report unacceptable behavior to [michel@cliqz.com](mailto:michel@cliqz.com).

## Ideas

**TODO** - move to issues tracker.

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

## MozSprint

Join us at the [Mozilla Global Sprint](http://mozilla.github.io/global-sprint/) June 1-2, 2017! We'll be gathering in-person at sites around the world and online to collaborate on this project and learn from each other. [Get your #mozsprint tickets now](http://mozilla.github.io/global-sprint/)!

![Global Sprint](https://cloud.githubusercontent.com/assets/617994/24632585/b2b07dcc-1892-11e7-91cf-f9e473187cf7.png)
