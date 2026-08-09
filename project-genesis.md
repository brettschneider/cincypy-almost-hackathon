# Project Genesis — Slack Conversation

Screenshot of a Slack conversation between Steve Brettschneider and Brian Sauer (handle `bsauer`), originating the "Almost Hackathon" idea. Brian's reply is captured below; the conversation continues past the screenshot's visible portion.

## Sunday, August 2nd

**Steve Brettschneider** — 10:00 PM

> Hey was thinking about the "hack-a-thon" idea that we talked about in the last meeting and what kind of "problem" we could ask people to solve in say 1.5 hours... assuming we'd have a 2 hour meeting and wanted to reserve 30 minutes for anyone that wanted to make a presentation. I asked Ollama for idea and it came back with a bunch of stuff that I thought was either too boring or to hard (for our crowd). But it DID give me an idea of something that could be done fairly easily with either an frontier API key or Ollama running purely locally. What if the challenge was something like this:
>
> > We want you to write a code-review agent. It should be an agent that accepts a single source-code file. The agent should review the source code file and return a "report" that includes the following sections:
> >
> > 1. What was done well in the source code file.
> > 2. What could be improved in the source code file.
> > 3. Identify any bugs or syntax errors in the source code file.
> > 4. (Extra credit bonus) A new version of the source code file with bugs fixed and made more efficient or readable.
> >
> > The input source code file could be in any major, common language: Python, JS, TS, C#, HTML, etc.
>
> We could leave it as vague as that on purpose to allow for creative solutions (is it a web page, a cli-tool, or something else... is the report a .pdf, an html page, etc.) We could stipulate in the rules, that you can use AI tools if you want, but they are not required nor disallowed. When we present them with the problem, we could also give them a handful of source code files that we create in advance:
>
> - One that's just broken with bad syntax.
> - One that runs but it's really inefficient and/or bloated.
> - One that is pretty good and shouldn't really need any modification.
> - One that is in a nonsensical language that doesn't exist.
> - One that's just an English paragraph.
>
> When we announce the hackathon, we could give some setup details (but NOT the problem obviously) so people can get their laptop ready ahead of time. We can include installation/setup instructions for Ollama in those details and/or I could even setup my own Ollama instance to run over the LAN if people don't want to set it up on their machine they can just call mine over HTTP. (It's just a REST API service with no auth)
>
> There would be no prizes or contest to this at all, Just show your creativity. I would not participate, but rather would float around helping anyone who needs/wants help.
>
> What do you think? (edited)
>
> Also the solution should be written in Python but that does without saying.

## Monday, August 3rd

**Brian Sauer (`bsauer`)** — 1:20 PM

> I like this idea, nice and text based. Gives time for people to prep but then the inputs are revealed at the meetup.

**Brian Sauer (`bsauer`)** — 1:35 PM

> Can you supply a list of "suggested technologies" and I can install/configure them and write some basic setup docs?
>
> Or I guess an LLM could do that 🙂

**Steve Brettschneider** — 10:27 PM

> I will try to write something up in the next day or so.

*(conversation continues past the visible screenshot)*
