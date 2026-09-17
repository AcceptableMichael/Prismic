# Testing flow

After you make changes, you may decide it's appropriate to run a suite of
tests, beyond "computer use", to test the new thing that you're building.

pytest-qt tests should be comprehensive. You should add / modify them as you
go. This is a UI-heavy application, so these will probably be the basis of
most automated testing. You may want to track the time duration it takes to
run these tests, in order to balance comprehensiveness vs. reality.

Code/logic unit tests should cover things as you feel appropriate.
