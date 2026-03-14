# LinkedIn Post 5: API Design - When Python Isn't Enough

A MATLAB user asked: "Can I use PyPLECS without learning Python?"

That question changed everything.

I'd built PyPLECS as a Python library. Great for Python users.

**But that's only 30% of the engineering community.**

The other 70%?
- MATLAB users
- JavaScript dashboards
- Excel automation
- C# enterprise systems

They all needed simulation access. None wanted to learn Python.

**The solution: REST API.**

Now anyone can run simulations:

```bash
# From curl
curl -X POST http://localhost:8000/simulations \
  -d '{"model": "buck.plecs", "Vi": 12.0}'

# From MATLAB
response = webwrite(url, struct('model', 'buck.plecs', 'Vi', 12.0))

# From JavaScript
fetch('/simulations', {method: 'POST', body: JSON.stringify({...})})
```

Same simulation engine. Any language.

**Adoption went up 3x in one month.**

The lesson? Build for the ecosystem, not just your favorite language.

API-first design = language-agnostic access = wider user base.

FastAPI gave us auto-generated docs, interactive testing, and OpenAPI schema for free.

What percentage of your potential users can't access your tool because of language barriers?

---

**GIF**: Animation of requests flowing from different languages (MATLAB, JS, Python, curl) into REST API

**Next post**: The Refactoring That Deleted 1,581 Lines

#APIDesign #SoftwareArchitecture #RESTful #Integration #FastAPI
