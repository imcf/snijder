# Snijder Development And Contribution Guide

## Making Changes

- Do [atomic commits][web_commit].
- For any change that consists of more than a single commit, create a topic
  branch.
- Check for unnecessary whitespace with `git diff --check` before committing.
- Make sure your commit messages are in a proper format.
  - Use the present tense ("Add feature" not "Added feature").
  - Use the imperative mood ("Change foo to..." not "Changes foo to...").
  - Limit the line length to 80 characters or less (72 for the first line).
  - Have the second line be empty.
  - If in doubt about the format, read [Tim Pope's note about git commit
    messages][web_tbaggery].

## Coding Conventions

- Python code follows [PEP-8][web_pep8] and [PEP-257][web_pep257].
- :memo: ToDo: add more details!

## Project Structure

The directory layout tries to follow the suggestions about clean Python project
structuring found in the following online resources:

- [Open Sourcing a Python Project the Right Way](https://jeffknupp.com/blog/2013/08/16/open-sourcing-a-python-project-the-right-way/)
- [Structuring Your Project](http://python-guide-pt-br.readthedocs.io/en/latest/writing/structure/)
- [Structure of a Python Project](http://www.patricksoftwareblog.com/structure-of-a-python-project/)
- [Repository Structure and Python](https://www.kennethreitz.org/essays/repository-structure-and-python)
- [A Project Skeleton](https://learnpythonthehardway.org/book/ex46.html)
- [SO: What is the best project structure for a Python application?](http://stackoverflow.com/questions/193161/what-is-the-best-project-structure-for-a-python-application)


[web_commit]: https://en.wikipedia.org/wiki/Atomic_commit#Atomic_commit_convention
[web_tbaggery]: https://tbaggery.com/2008/04/19/a-note-about-git-commit-messages.html
[web_pep8]: https://www.python.org/dev/peps/pep-0008/
[web_pep257]: https://www.python.org/dev/peps/pep-0257/