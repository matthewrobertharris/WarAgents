package model.output;

import java.io.ByteArrayOutputStream;
import java.io.PrintStream;

import org.junit.After;
import org.junit.Test;

import junit.framework.TestCase;
import main.Game;
import model.Agent;
import model.Map;
import model.output.Action.Activity;
import readers.ActionReaderImpl;
import readers.CriteriaReaderImpl;
import readers.GameReader;
import readers.GameReaderImpl;
import readers.InputReaderImpl;
import readers.MapReaderImpl;
import readers.ModeReaderImpl;
import readers.PlantReaderImpl;
import readers.PlayerReaderImpl;
import readers.PositionReaderImpl;
import readers.TreeReaderImpl;

public class TestAttackDown extends TestCase {

	private GameReader gameReader;
	private final ByteArrayOutputStream outContent = new ByteArrayOutputStream();

	@Override
	protected void setUp() {
		gameReader = new GameReaderImpl(new MapReaderImpl(new PlantReaderImpl(),
				new PlayerReaderImpl(new TreeReaderImpl(new ActionReaderImpl(new PositionReaderImpl()), new InputReaderImpl(new PositionReaderImpl()))),
				new CriteriaReaderImpl(new ActionReaderImpl(new PositionReaderImpl())), new ModeReaderImpl()));
		System.setOut(new PrintStream(outContent));
	}
	
	@After
	public void cleanUpStreams() {
	    System.setOut(null);
	}

	/**
	 * http://stackoverflow.com/questions/1119385/junit-test-for-system-out-println
	 */
	@Test
	public void testAttackDown_Success_2Survive() {
		String file = "resources\\test\\outputMaps\\test_attackDown_success_2survive.map";
		Game game = gameReader.readGame(file);
		Map map = game.getMap();
		Agent agent = map.getAllAgents().get(0);
		
		assertTrue(agent.update(map));
		assertTrue(agent.getAction().getActivity() == Activity.ATTACK_DOWN);
		assertTrue(map.getAllAgents().size() == 2);
	}
	
	@Test
	public void testAttackDown_Success_DefenderDeath() {
		String file = "resources\\test\\outputMaps\\test_attackDown_success_defenderDeath.map";
		Game game = gameReader.readGame(file);
		Map map = game.getMap();
		Agent agent = map.getAllAgents().get(0);
		
		assertTrue(agent.update(map));
		assertTrue(agent.getAction().getActivity() == Activity.ATTACK_DOWN);
		assertTrue(map.getAllAgents().size() == 1);
	}
	
	@Test
	public void testAttackDown_Fail_NoAgent() {
		String file = "resources\\test\\outputMaps\\test_attackDown_fail_noAgent.map";
		String error = "Cannot ATTACK_DOWN because no agent to attack\r\n";
		Game game = gameReader.readGame(file);
		Map map = game.getMap();
		Agent agent = map.getAllAgents().get(0);
		
		assertFalse(agent.update(map));
		assertTrue(agent.getAction().getActivity() == Activity.ATTACK_DOWN);
		assertTrue(map.getAllAgents().size() == 1);
		assertEquals(outContent.toString(), error);
	}
	
	@Test
	public void testAttackDown_Fail_OutOfBounds() {
		String file = "resources\\test\\outputMaps\\test_attackDown_fail_outofbounds.map";
		String error = "Cannot ATTACK_DOWN because attack is out of bounds\r\n";
		Game game = gameReader.readGame(file);
		Map map = game.getMap();
		Agent agent = map.getAllAgents().get(0);
		
		assertFalse(agent.update(map));
		assertTrue(agent.getAction().getActivity() == Activity.ATTACK_DOWN);
		assertTrue(map.getAllAgents().size() == 1);
		assertEquals(outContent.toString(), error);
	}
	

	@Test
	public void testAttackDown_Success_Height1() {
		String file = "resources\\test\\outputMaps\\test_attackDown_success_height1.map";
		Game game = gameReader.readGame(file);
		Map map = game.getMap();
		Agent agent = map.getAllAgents().get(0);
		int power = agent.getPower();
		Agent defender = map.getAllAgents().get(1);
		int health = defender.getHealth();
		
		assertTrue(agent.update(map));
		assertTrue(agent.getAction().getActivity() == Activity.ATTACK_DOWN);
		assertTrue(map.getAllAgents().size() == 2);
		assertTrue(defender.getHealth() == (health - (2 * power)));
	}
	
	@Test
	public void testAttackDown_Success_Height2() {
		String file = "resources\\test\\outputMaps\\test_attackDown_success_height2.map";
		Game game = gameReader.readGame(file);
		Map map = game.getMap();
		Agent agent = map.getAllAgents().get(0);
		int power = agent.getPower();
		Agent defender = map.getAllAgents().get(1);
		int health = defender.getHealth();
		
		assertTrue(agent.update(map));
		assertTrue(agent.getAction().getActivity() == Activity.ATTACK_DOWN);
		assertTrue(map.getAllAgents().size() == 2);
		assertTrue(defender.getHealth() == (health - (3 * power)));
	}
	
	@Test
	public void testAttackDown_Success_Height3() {
		String file = "resources\\test\\outputMaps\\test_attackDown_success_height3.map";
		Game game = gameReader.readGame(file);
		Map map = game.getMap();
		Agent agent = map.getAllAgents().get(0);
		int power = agent.getPower();
		Agent defender = map.getAllAgents().get(1);
		int health = defender.getHealth();
		
		assertTrue(agent.update(map));
		assertTrue(agent.getAction().getActivity() == Activity.ATTACK_DOWN);
		assertTrue(map.getAllAgents().size() == 2);
		assertTrue(defender.getHealth() == (health - (4 * power)));
	}
	
	@Test
	public void testAttackDown_Fail_Height4() {
		String file = "resources\\test\\outputMaps\\test_attackDown_fail_height4.map";
		String error = "Cannot ATTACK_DOWN because attack failed\r\n";
		Game game = gameReader.readGame(file);
		Map map = game.getMap();
		Agent agent = map.getAllAgents().get(0);
		Agent defender = map.getAllAgents().get(1);
		int health = defender.getHealth();
		
		assertFalse(agent.update(map));
		assertTrue(agent.getAction().getActivity() == Activity.ATTACK_DOWN);
		assertTrue(map.getAllAgents().size() == 2);
		assertTrue(defender.getHealth() == (health));
		assertEquals(outContent.toString(), error);
	}
	
	@Test
	public void testAttackDown_Fail_HeightMinus3() {
		String file = "resources\\test\\outputMaps\\test_attackDown_fail_height-3.map";
		String error = "Cannot ATTACK_DOWN because attack failed\r\n";
		Game game = gameReader.readGame(file);
		Map map = game.getMap();
		Agent agent = map.getAllAgents().get(0);
		Agent defender = map.getAllAgents().get(1);
		int health = defender.getHealth();
		
		assertFalse(agent.update(map));
		assertTrue(agent.getAction().getActivity() == Activity.ATTACK_DOWN);
		assertTrue(map.getAllAgents().size() == 2);
		assertTrue(defender.getHealth() == (health));
		assertEquals(outContent.toString(), error);
	}
	
	@Test
	public void testAttackDown_Success_HeightMinus1() {
		String file = "resources\\test\\outputMaps\\test_attackDown_success_height-1.map";
		Game game = gameReader.readGame(file);
		Map map = game.getMap();
		Agent agent = map.getAllAgents().get(0);
		int power = agent.getPower();
		Agent defender = map.getAllAgents().get(1);
		int health = defender.getHealth();
		
		assertTrue(agent.update(map));
		assertTrue(agent.getAction().getActivity() == Activity.ATTACK_DOWN);
		assertTrue(map.getAllAgents().size() == 2);
		assertTrue(defender.getHealth() == (health - (power / 2)));
	}
	
	@Test
	public void testAttackDown_Success_HeightMinus2() {
		String file = "resources\\test\\outputMaps\\test_attackDown_success_height-2.map";
		Game game = gameReader.readGame(file);
		Map map = game.getMap();
		Agent agent = map.getAllAgents().get(0);
		int power = agent.getPower();
		Agent defender = map.getAllAgents().get(1);
		int health = defender.getHealth();
		
		assertTrue(agent.update(map));
		assertTrue(agent.getAction().getActivity() == Activity.ATTACK_DOWN);
		assertTrue(map.getAllAgents().size() == 2);
		assertTrue(defender.getHealth() == (health - (power / 3)));
	}
}
