from agentmint import Notary, notarise

notary = Notary()


@notarise(notary, action="quickstart:hello")
def greet(name):
    return {"message": f"hello {name}"}


if __name__ == "__main__":
    print(greet("world"))
