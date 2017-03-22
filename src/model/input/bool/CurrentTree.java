package model.input.bool;

import model.Agent;
import model.Map;
import model.input.DecisionBoolean;

public class CurrentTree extends DecisionBoolean {

	private String tree;
	
	public CurrentTree(String tree) {
		setTree(tree);
	}
	
	public String getTree() {
		return tree;
	}

	public void setTree(String tree) {
		this.tree = tree;
	}

	@Override
	public boolean decide(Agent agent, Map map) throws Exception {
		return agent.getTree().getName().equals(getTree());
	}

	public String toString() {
		String output = Option.CURRENT_TREE.toString() + " " + getTree();
		return output;
	}
	
}
