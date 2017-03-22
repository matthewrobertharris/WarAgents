package model.input.numeric;

import model.Agent;
import model.Map;
import model.Player;
import model.input.DecisionNumeric;

public class NumberTrees extends DecisionNumeric {

	private String tree;
	
	public NumberTrees(String tree) {
		setTree(tree);
	}
	
	public String getTree() {
		return tree;
	}

	public void setTree(String tree) {
		this.tree = tree;
	}

	@Override
	public int decide(Agent agent, Map map) throws Exception {
		Player player = agent.getPlayer();
		int count = 0;
		for(Agent a : player.getCurrentAgents()) {
			String tree = a.getTree().getName();
			if(tree.equals(getTree())) {
				count += 1;
			}
		}
		return count;
	}

	public String toString() {
		String output = Option.NUMBER_TREES.toString() + " " + getTree();
		return output;
	}

}
