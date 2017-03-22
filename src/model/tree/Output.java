package model.tree;

import model.output.Action;

public class Output extends Node {
	
	private Action action;

	public Output(Node parent, Action action, Tree tree) {
		super(parent, tree);
		setAction(action);
	}

	public Action getAction() {
		return action;
	}

	public void setAction(Action action) {
		this.action = action;
	}

	public String toString() {
		String output = "(" + getTree().getName() + "|" + getAction().toString() + ")";
		return output;
	}
}
